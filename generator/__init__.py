
from __future__ import annotations
import os
import time
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import textwrap

from tqdm import tqdm

from openai import OpenAI


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)


MAX_RETRIES = 5


# ---------------------------------------------------------------------------
# Minimal .env loader (no extra dependency)
# ---------------------------------------------------------------------------
def _load_dotenv(path: "str | os.PathLike | None" = None) -> None:
    """Load KEY=VALUE lines from a .env file into os.environ.

    Does not overwrite variables already present in the environment, so an
    explicit `export` / shell value always wins. Silently no-ops if absent.
    """
    if path is None:
        path = Path(__file__).resolve().parent.parent / ".env"
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()


# ---------------------------------------------------------------------------
# Model roles (single source of truth)
# ---------------------------------------------------------------------------
# Policy   = the model we are training (Laguna). Used for the trainable-band gate
#            (keep tasks where 0 < pass@k < 1 so RL reward variance is non-zero).
# Reference= a frontier model (GPT-5.5). Used as the validity / solvable-at-all
#            gate and as the tie-breaker on tasks the policy never solves.
POLICY_MODEL = os.environ.get("POLICY_MODEL", "laguna")
REFERENCE_MODEL = os.environ.get("REFERENCE_MODEL", "gpt-5.5")


def summary_filename(model: str) -> str:
    """Per-task solutions summary filename for a given solver model."""
    return f"{model.replace('/', '_')}_summary.json"


# ---------------------------------------------------------------------------
# Backend routing
# ---------------------------------------------------------------------------
# Three backends, chosen by model name so existing task-GENERATION code (which
# passes local models like Qwen/Qwen3-32B) is unaffected:
#   - "laguna*"            -> the Laguna policy endpoint (Modal vLLM, OpenAI API)
#   - "gpt-*"/"o1|o3|o4*"  -> the real OpenAI API (frontier validity gate)
#   - everything else      -> the local vLLM server used for generation
def _is_openai_reasoning(model: str) -> bool:
    m = (model or "").lower()
    return m.startswith("gpt-5") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4")


def _resolve_backend(model: "str | None") -> Dict[str, Any]:
    m = (model or "").lower()
    if m.startswith("laguna"):
        base = os.environ.get("LAGUNA_API_BASE")
        if not base:
            raise RuntimeError(
                "LAGUNA_API_BASE not set (see .env). Needed to route the 'laguna' policy model."
            )
        return {
            "kind": "laguna",
            "base_url": base,
            "api_key": os.environ.get("LAGUNA_API_KEY", "nokey"),
            "reasoning": False,
            "timeout": 600.0,
        }
    if m.startswith("gpt-") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4"):
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError(
                f"OPENAI_API_KEY not set (see .env). Needed to route OpenAI model '{model}'."
            )
        return {
            "kind": "openai",
            "base_url": None,  # default https://api.openai.com/v1
            "api_key": key,
            "reasoning": _is_openai_reasoning(model),
            "timeout": 600.0,
        }
    return {
        "kind": "local",
        "base_url": "http://localhost:8000/v1",
        "api_key": "nokey",
        "reasoning": False,
        "timeout": 600.0,
    }


def chat_completion_batch(
    messages: List[List[Dict[str, str]]],
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    num_completions: int = 1,
    max_concurrency: int = 64,
    show_progress: bool = True,
) -> List[Any]:
    """Submit multiple chat completion requests concurrently.

    The backend (local vLLM / Laguna endpoint / OpenAI) is chosen from `model`,
    so the same call site serves task generation (local), the policy band gate
    (Laguna), and the frontier validity gate (OpenAI).
    """
    backend = _resolve_backend(model)
    client = OpenAI(
        base_url=backend["base_url"],
        api_key=backend["api_key"],
        timeout=backend["timeout"],
    )
    is_reasoning = backend["reasoning"]
    max_retries = MAX_RETRIES

    def _create(msgs: List[Dict[str, str]]):
        kwargs: Dict[str, Any] = {"model": model, "messages": msgs, "n": num_completions}
        if is_reasoning:
            # OpenAI reasoning models (o-series, gpt-5*): use max_completion_tokens
            # and the fixed default temperature (custom temperature is rejected).
            kwargs["max_completion_tokens"] = max_tokens
            kwargs["reasoning_effort"] = os.environ.get("OPENAI_REASONING_EFFORT", "low")
        else:
            kwargs["max_tokens"] = max_tokens
            kwargs["temperature"] = temperature
        return client.chat.completions.create(**kwargs)

    def _one_with_retry(idx: int, msgs: List[Dict[str, str]]):
        """Execute a single request with retry logic."""
        last_error = None

        for attempt in range(max_retries):
            try:
                return _create(msgs)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if attempt < max_retries - 1:
                    if "rate" in error_str:
                        wait_time = min(2 ** (attempt + 2), 30)  # Rate limit backoff
                    elif "timeout" in error_str:
                        wait_time = 2  # Short wait for timeout
                    else:
                        wait_time = 2 ** attempt  # General exponential backoff
                    time.sleep(wait_time)
                else:
                    raise last_error

    results: List[Any] = [None] * len(messages)

    # Process requests concurrently
    with ThreadPoolExecutor(max_workers=max_concurrency) as pool:
        future_to_idx = {
            pool.submit(_one_with_retry, i, m): i
            for i, m in enumerate(messages)
        }

        pbar = tqdm(
            total=len(messages),
            disable=not show_progress,
            dynamic_ncols=True,
            desc="Processing",
            unit="req",
            miniters=1,
            file=sys.stdout,
        )
        try:
            for fut in as_completed(future_to_idx):
                idx = future_to_idx[fut]
                try:
                    results[idx] = fut.result()
                except Exception:
                    results[idx] = None  # Mark as failed
                finally:
                    pbar.update(1)
        finally:
            pbar.close()

    failed_indices = [i for i, r in enumerate(results) if r is None]
    if failed_indices:
        logger.warning(f"Failed requests: {failed_indices}")

    return results


def parse_python_code(code: str) -> str:
    """Extract the raw Python code from an LLM response string.

    The language-model may wrap the code in Markdown triple-backtick fences
    (optionally annotated with a language tag like ``python``) or include
    additional explanatory text.  This helper returns **only** the actual
    Python source, trimmed and left-dedented so it can be written directly
    to a ``.py`` file.
    """
    import re
    # First, look for a fenced code block – we assume the first one contains
    # the pytest file we are interested in.
    fence_regex = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL | re.IGNORECASE)
    match = fence_regex.search(code)
    if match:
        snippet = match.group(1)
    else:
        # Fallback – treat the whole string as code.
        snippet = code
    # Normalise indentation & strip trailing whitespace/newlines
    return textwrap.dedent(snippet).rstrip()  # type: ignore[arg-type]

def check_python_code(code: str) -> bool:
    """Check if the Python code compiles successfully."""
    try:
        compile(code, "<string>", "exec")
        return True
    except SyntaxError:
        return False
    except Exception:
        return False
