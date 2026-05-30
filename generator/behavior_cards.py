"""Behavior-conditioned task cards for Laguna meta-control training.

The cards are deterministic control inputs for the existing LLM generation
funnel. They do not replace the funnel; they constrain each generated task to
exercise a TRACE-style capability axis inferred from Laguna/TBLite rollouts.
"""
from __future__ import annotations

import random
from typing import Any, Dict, Iterable, List


BEHAVIOR_CARDS: List[Dict[str, Any]] = [
    {
        "id": "exit_code_false_success",
        "capability": "verification_directed_action",
        "observed_behavior": (
            "Laguna treats exit_code=0 or a clean script run as success even when "
            "the required deliverable is missing, incomplete, or semantically wrong."
        ),
        "source_traces": [
            "book-portfolio-analysis",
            "pandas-numpy-data-analysis",
            "jsonl-aggregator",
            "csv-json-jsonl-merger",
        ],
        "task_affordance": (
            "Include an obvious implementation that exits cleanly while producing "
            "a subtly wrong artifact. Success must require checking the artifact "
            "against an invariant that is visible from the task data."
        ),
        "required_pivot": (
            "After a clean-but-wrong run, inspect the output artifact and change "
            "the data-processing logic rather than rerunning the same command."
        ),
        "reward_observable": (
            "Prefix checkpoints should distinguish command completion, artifact "
            "existence, artifact validity, semantic correctness, and verified stop."
        ),
        "next_capability": (
            "Turn command-level success into deliverable-level verification and "
            "use verifier evidence to choose the next action."
        ),
    },
    {
        "id": "repeat_loop_after_dead_end",
        "capability": "recognition_to_action_coupling",
        "observed_behavior": (
            "Laguna sometimes states that it is stuck or needs a different approach "
            "but re-emits a byte-identical or near-identical command."
        ),
        "source_traces": [
            "pgn-chess-repair-puzzles",
            "book-portfolio-analysis",
            "bash-log-processor-fix",
        ],
        "task_affordance": (
            "Create a designed dead-end where retrying the same action cannot "
            "change state. A different command class or algorithmic formulation "
            "must be required to advance."
        ),
        "required_pivot": (
            "Recognize unchanged state, name the failed assumption implicitly in "
            "the next action, and switch to a semantically different operation."
        ),
        "reward_observable": (
            "Reward only action changes that coincide with prefix progress; do "
            "not reward superficial command diversity."
        ),
        "next_capability": (
            "Bind reflection/stuckness recognition to a concrete new action that "
            "moves the task state."
        ),
    },
    {
        "id": "wander_loop_without_convergence",
        "capability": "bounded_search_discipline",
        "observed_behavior": (
            "Laguna can emit many distinct commands across the full turn budget "
            "while failing to converge or stop."
        ),
        "source_traces": [
            "parking-lot-pathfinding",
            "acl-permissions-inheritance",
            "grid-pathfinding",
            "permutation-construction-100k",
        ],
        "task_affordance": (
            "Require search or diagnosis over several plausible hypotheses, but "
            "make each step produce evidence that should narrow the next action."
        ),
        "required_pivot": (
            "Maintain a compact hypothesis/progress state and eliminate failed "
            "branches instead of trying unrelated commands."
        ),
        "reward_observable": (
            "Checkpoint evidence collection, branch elimination, correct final "
            "choice, and stopping after verification."
        ),
        "next_capability": (
            "Convert action entropy into disciplined search with convergence."
        ),
    },
    {
        "id": "premature_stop_on_sparse_feedback",
        "capability": "stop_continue_calibration",
        "observed_behavior": (
            "Laguna sometimes stops after one or two turns when sparse or quiet "
            "feedback leaves the final state unverified."
        ),
        "source_traces": [
            "build-system-task-ordering",
            "application-debug",
            "reproducibility-and-envsetup",
        ],
        "task_affordance": (
            "Make early commands return little or no output while the task still "
            "requires inspecting files, running a targeted check, or producing a "
            "specific artifact."
        ),
        "required_pivot": (
            "Treat silence as insufficient evidence, continue with a verification "
            "command, and stop only after the final invariant is checked."
        ),
        "reward_observable": (
            "Penalize early stop before the deliverable exists and reward final "
            "stop only after verification."
        ),
        "next_capability": (
            "Calibrate stop/continue decisions under sparse feedback."
        ),
    },
    {
        "id": "old_state_new_state_confusion",
        "capability": "stateful_migration_verification",
        "observed_behavior": (
            "Laguna can perform a plausible rewrite or migration but validate the "
            "old state, stale path, or wrong source of truth."
        ),
        "source_traces": [
            "db-migration-local-storage",
            "multi-server-configuration",
            "api-endpoint-permission-canonica",
        ],
        "task_affordance": (
            "Require changing where truth lives: migrate data, rotate config, "
            "switch endpoints, or retire an old path while preserving semantics."
        ),
        "required_pivot": (
            "After modifying state, query the new source of truth and detect stale "
            "success signals from the old location."
        ),
        "reward_observable": (
            "Checkpoint old-state detection, new-state creation, data preservation, "
            "old-path retirement, and verified service/artifact behavior."
        ),
        "next_capability": (
            "Track evolving task state across writes and verify the final state in "
            "the correct location."
        ),
    },
    {
        "id": "partial_progress_stall",
        "capability": "long_horizon_progress_ledger",
        "observed_behavior": (
            "Laguna reaches a partially correct state and then loops, wanders, or "
            "stops without completing the remaining constraints."
        ),
        "source_traces": [
            "security-incident-log-analysis",
            "security-breach-incident-respons",
            "bash-log-processor-fix",
            "server-log-analysis",
        ],
        "task_affordance": (
            "Use multi-constraint tasks where early subgoals are easy but final "
            "success requires preserving all prior constraints while satisfying "
            "one or two later invariants."
        ),
        "required_pivot": (
            "Maintain a checklist of satisfied and unsatisfied constraints, then "
            "target the remaining failing invariant without regressing earlier ones."
        ),
        "reward_observable": (
            "Use longest-prefix or gated checkpoints so farming independent partial "
            "credit is not enough."
        ),
        "next_capability": (
            "Carry a progress ledger across turns and finish the last hard constraint."
        ),
    },
]


def iter_behavior_cards() -> Iterable[Dict[str, Any]]:
    return tuple(BEHAVIOR_CARDS)


def sample_behavior_cards(
    count: int,
    seed: int | None = None,
    card_ids: Iterable[str] | None = None,
) -> List[Dict[str, Any]]:
    """Return a deterministic shuffled cycle of behavior cards."""
    rng = random.Random(seed)
    cards = list(BEHAVIOR_CARDS)
    if card_ids is not None:
        requested = list(card_ids)
        by_id = {card["id"]: card for card in cards}
        unknown = sorted(set(requested) - set(by_id))
        if unknown:
            raise ValueError(f"Unknown behavior card id(s): {', '.join(unknown)}")
        cards = [by_id[card_id] for card_id in requested]
    if not cards:
        raise ValueError("At least one behavior card is required")
    out: List[Dict[str, Any]] = []
    while len(out) < count:
        shuffled = list(cards)
        rng.shuffle(shuffled)
        out.extend(shuffled)
    return out[:count]


def format_behavior_prompt(card: Dict[str, Any]) -> str:
    traces = ", ".join(card["source_traces"])
    return (
        "Behavior-conditioned capability target:\n"
        f"- card_id: {card['id']}\n"
        f"- next_capability: {card['next_capability']}\n"
        f"- observed Laguna/TBLite behavior: {card['observed_behavior']}\n"
        f"- source trace motifs: {traces}\n"
        f"- task affordance to instantiate: {card['task_affordance']}\n"
        f"- required pivot: {card['required_pivot']}\n"
        f"- verifier/reward observable: {card['reward_observable']}\n"
        "Generate a realistic terminal task that hillclimbs this capability. "
        "The task should be solvable by a capable terminal agent, but the shortest "
        "path to reliable success must exercise the next capability above."
    )
