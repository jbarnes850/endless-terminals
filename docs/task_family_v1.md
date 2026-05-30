# Task Family v1 - Progress-Legible Terminal Tasks

Status: design draft (2026-05-29). Scopes the first Endless Terminals task family
for the Laguna-XS.2 process-grounded RL run.

## Why this family exists

The native-tool-calling baseline isolated a single deficit in Laguna: it is
closed-loop at the command level (it fixes an immediate command error in one
turn) and open-loop at the task level (no maintained progress state, so it
neither detects non-progress nor recognizes completion). The signatures:

- never-stop loops: identical/near-identical actions to the 40-cap, reading
  `exit_code=0` as success while never checking the deliverable.
- thought-action decoupling: it verbally announces a pivot, then re-emits the
  same action.
- premature-stop: ends after 1-2 turns when nothing comes back.
- Reflection is the sparsest codebook group; its absence is the loopers' fingerprint.

This family is not a capability test. It is an instrument to make the missing
control loop trainable: dense progress signal, a deliverable check that cannot be
faked by exit codes, a designed dead-end that forces a change of approach, and an
unambiguous done-state so the stop decision is learnable.

## Verified against the live full baseline (40/100 completed, 2026-05-29)

Classifying the 40 completed full-TBLite tasks (native agent) confirms the premise and
corrects one bias inherited from the 11-trace sample:

- Loop is the dominant FAILURE mode: pass 40%, loop 25%, clean-fail 22%, partial 8%,
  premature-stop 5%. Loop (10) is the single largest failure bucket.
- `stop=False` is the perfect loop discriminator: all 10 loopers hit the 40-cap without
  ever emitting a final/stop message; every non-looper stopped. Turn-exhaustion, not
  command diversity, is the clean signal.
- `exit_code=0`-as-success is real: loopers see 26-40 exit_code=0 tool results while
  scoring 0. Validates the deliverable-distinct-from-exit-code invariant.
- premature-stop is the minor pole (2/40), one of which is the known native long-XML
  drop (build-system). Design correctly deprioritizes it.

CORRECTION (bias in the 11-trace sample): all four historical loopers were the
VERBATIM-REPEAT sub-type (same command 11-33x). The full sweep shows loops are BIMODAL:
~half are verbatim-repeat (pdf-table-parsing/pgn-chess maxRep=30, ekf=28) and ~half are
WANDERERS that emit ~40 DISTINCT commands and still never converge or stop
(acl-permissions/parking-lot uniq=40 maxRep=1, multi-server/systemd/symlink uniq 34-38).
The wanderer is consistent with CISPO preserving action entropy: Laguna already explores;
it cannot tell it is not progressing and cannot stop. This sharpens the thesis (the
deficit is progress-tracking + stop, NOT exploration) and forces design corrections:

1. STOP-QUALITY is the highest-signal target (perfect discriminator) — already the
   dominant reward term; keep it dominant.
2. The action-change credit MUST be strictly gated on prefix-advance. Ungated, it would
   reward the wanderers' churn (they change actions every turn). The "AND advances the
   prefix" conjunct is load-bearing, not optional.
3. The pure turn-level exploration term (A^2TGPO/AEPO) is DE-PRIORITIZED for Laguna: it
   already has action diversity. Spend the lever budget on progress + stop, not entropy.
4. Eval metric: use turn-exhaustion / stop-at-cap rate as the PRIMARY loop metric.
   Command diversity (the ET paper's 0.18-vs-0.49 dial) UNDER-COUNTS Laguna loops because
   wanderers have diversity ~1.0; keep it only as a secondary, repeat-type-only signal.
5. C1 mainly exercises the repeat sub-type. Add a search/constraint category (no give-up)
   to exercise the wanderer, or ensure C1 instances include both, before v2.

## Four design invariants (every task satisfies all four)

1. Staged with PREFIX-GATED checkpoints. Each task has K ordered sub-goals, each
   verified by its own assertion in `test_final_state.py`, ordered validity ->
   semantic repair/migration -> downstream query/probe -> final artifact ->
   done-state. Progress is the LONGEST SATISFIED PREFIX, not the raw satisfied
   count: assertion `A_i` only credits if `A_1..A_{i-1}` also pass. This forces
   monotone progress (no farming a later checkpoint that happens to pass first) and
   is the structure the reward shaping reads. The test file and per-turn reward
   values are NEVER visible to the policy during rollout (anti-leak); only the
   environment's natural stdout/stderr is observable.

2. Deliverable distinct from exit code. Final-state assertions check the artifact
   itself (file contents, parsed values, structural properties), never "a command
   ran." This removes the `exit_code=0 == done` false signal that drives the loopers'
   asymmetric verification.

3. A designed dead-end. The obvious first approach hits a wall that a retry cannot
   clear; only a different action clears it (e.g., the naive parser chokes on a real
   edge case; the server port is already bound; a unicode record slips a filter).
   This is the exact recognition->change-action coupling we are training. The band
   filter guarantees Laguna sometimes escapes it (otherwise no gradient).

4. Unambiguous terminal state. Exactly one checkable "done" condition, so the stop
   decision is well defined and rewardable: +stop-when-complete, -stop-early,
   -run-past-complete.

## Categories (each maps to a failure mode), seeded from OpenThoughts-Agent-v1-RL

OpenThoughts-Agent-v1-RL (728 tasks, columns `path` + `task_binary`, a packed
task archive; terminal/SWE agentic style, the SFT/RL set behind OpenThinker-Agent-v1)
is the structural seed and difficulty anchor. We do not reuse its binary verifiers
verbatim; we decompose each adapted task into per-checkpoint assertions.

| # | Category | Failure mode targeted | Staging / dead-end |
|---|----------|----------------------|--------------------|
| C1 | Parse-then-transform (malformed data repair -> constrained query) | never-stop loop; exit_code=0 false signal | Stage A repair malformed JSON/CSV with a real edge case (a unicode or trailing-comma record that passes a naive `isalpha`/split filter); Stage B answer a query over the repaired data. The naive repair runs cleanly but produces wrong data -> deliverable check fails even at exit 0. |
| C2 | Service bring-up + probe (start a server, hit an endpoint, capture output) | loop on a retried failing action; no goal check | Dead-end: the init-started server already holds the port; relaunching never binds. Escape requires killing/relocating, not retrying. Checkpoints: server reachable, correct response captured, artifact written. |
| C3 | Build/compile + targeted test | premature-stop; long-payload action | Multi-file build where one file has a latent bug a single test catches. Checkpoints: builds, test runs, test passes, fix is minimal. Targets the premature-stop pole and verify-before-stop. |
| C4 | Multi-step migration with verification | thought-action decoupling; run-past-done | Migrate data store / format; the correctness check requires querying the NEW state, not the old. Checkpoints: schema migrated, rows preserved, old path retired, new path serves. Rewards stop-when-verified. |
| C5 | Search / constraint-satisfaction with a give-up option | never-stop on an unsolvable-as-approached instance | Combinatorial task (mapping/derangement style) where one approach class cannot succeed; a different formulation can. Task text explicitly permits giving up. Trains both change-approach and an honest stop. |

Each category ships 6-10 instances at varied difficulty so the band filter has a
population to bucket. C1 and C5 directly reproduce two of the four observed loopers
(book-portfolio / pandas-numpy), which makes them the highest-signal starting point.

## Seeding and conversion pipeline

1. Pull OpenThoughts-Agent-v1-RL; unpack `task_binary` for a sample to confirm the
   archive layout (Dockerfile/tests/solution/task spec, terminal-bench style).
2. Select instances matching C1-C5 by category/keyword.
3. Adapt to Endless Terminals format, preserving the truth<->description integrity
   invariant: secret ground truth only in `<truth>`, public text in `description`,
   `test_initial_state.py` + `test_final_state.py` written from the truth with one
   assertion per checkpoint, `container.def` bootstrapping the environment.
4. For genuinely fresh instances (C5 variants), use the existing 4-stage generator
   with the GPT-5.5 reference now wired in.

## Filtering (uses the admission and band gates)

- Build SIFs and admit only executable Apptainer environments: normalized
  `container.def` builds to `container.sif`, the SIF starts with the same
  interactive runtime used for rollouts, initial tests pass, the `/home/user`
  shell accepts a benign command, and the final verifier can be invoked as a
  valid pass/fail signal. Only that eligible manifest may feed Laguna
  calibration.
- Run `scripts/run_eligible_calibration.py --model laguna` to produce
  `laguna_summary.json` per admitted task (band gate, our Modal endpoint).
- `python -m generator.task_filters --tasks-dir <dir> --group-size <G> --max-zero-std-group-frac 0.5`
  -> keep the `trainable` bucket (0 < Laguna pass@k < 1), and drop band tasks whose
  expected zero-advantage group fraction exceeds the RLVR HARD-STOP threshold.
- Run GPT-5.5 only on the `needs_reference` (Laguna-zero) tasks to split
  `too_hard_valid` (keep as curriculum) from `broken` (drop).
- Escape-trace gate (causal, not just outcome): a task counts as trainable only if at
  least one passing Laguna rollout shows dead-end-signal -> a semantically different
  next action -> prefix advance. v1 proxy: >= 2 distinct command classes after the
  first failed/non-progress turn in a passing trace. Without this, `0 < pass@k < 1`
  can be a lucky direct solve that never exercised recognition->change-action.
- `prepare_endless.py --gate band` builds the train/val parquet from the trainable set.

## Reward (how the family plugs into training)

Hardened against partial-checkpoint harvesting (the dominant reward hack: farm cheap
early assertions, avoid risky finalization, jitter state to dodge the loop penalty).

- Progress potential: shaping on the LONGEST SATISFIED PREFIX (potential-based; ProgRM
  / VPR style, grounded in the per-checkpoint oracle). Because progress is the prefix,
  a later-checkpoint accident pays nothing; only advancing the frontier pays.
- Final-completion + stop-quality DOMINATE the return. Partial progress is a small
  shaping term; the bulk of reward is task-complete AND stopped-correctly. A
  non-completing partial-harvester must score well below a completer.
- Action-change credit (the coupling term): positive reward when, after a failure /
  non-progress signal, the next action is semantically different (different command
  class / target) AND that change advances the prefix. This directly trains
  recognition->changed-action, which diversity preservation alone will not (Codex
  point: token-entropy is already healthy; the inertia is action-level).
- Non-progress penalty: negative when environment state is unchanged across a turn,
  hardened so trivial state churn (touch a file, echo) does not reset it; it keys on
  whether the prefix advanced, not on raw byte-diff.
- Stop quality: +stop-when-complete, -stop-early, -run-past-complete, from the
  terminal-state checkpoint.
- Optimization: preserve action diversity at the turn level (A^2TGPO-style turn
  clipping / AEPO), consistent with the baseline finding that the deficit is
  action-level, not token-level.

## Size and 12h scope

- v1 trains on C1 ONLY (parse-then-transform). It reproduces two of the four observed
  loopers, hits the `exit_code=0` false-success signal head-on, is cheapest to
  generate, and has clean artifact-level checks. C2/C3/C4 add capability variance;
  C5's give-up confounds the stop decision. They are deferred to v2.
- Target ~24-40 C1 instances at varied difficulty (enough population for the band
  filter), held-out eval split disjoint from train.
- Protocol is DECIDED UP FRONT (see Pre-commit gate): filter, train, and eval all in
  the same action protocol, or pass@k banding and the loop-rate delta are not portable.
- Pre-registered eval (primary -> secondary): turn-exhaustion / stop-at-cap rate
  (the perfect loop discriminator in the baseline), correct-stop rate, pass@k on the
  held-out split; command diversity kept only as a secondary repeat-type signal (it
  under-counts wanderer loops). All measured on the baseline before training.

## Pre-commit gate (run before spending the 12h)

The weakest assumption is that band-selected C1 tasks actually train recognition->
change-action rather than rewarding lucky direct solves. Test it cheaply first:

1. Pick ~8 C1 candidates. Run Laguna at k rollouts each, no training, in the chosen
   protocol. Decide protocol here by smoke-testing both: the `<command>` text protocol
   (simpler than the terminus-2 JSON that caused the death-spiral) vs native
   tool-calling. Lock whichever Laguna drives cleanly without format failures.
2. Replay the proposed prefix-gated reward over the rollouts. Manually label each
   passing trace: did reward increments occur AT the pivot (dead-end observed -> action
   changed -> prefix advanced), or before it? Do non-completing partial-harvesters
   score well below completers under the dominant final/stop terms?
3. Kill or redesign if reward mostly increments before the pivot, or if harvesters
   score close to passers. Proceed only if the reward credits the pivot and completion
   dominates.

## Open risks

- Seed conversion can silently break validity; the band filter (Laguna pass@k > 0 as a
  side effect) plus the GPT-5.5 tie-breaker catch most of it.
- Protocol mismatch is first-order, decided in the Pre-commit gate: ET ships the
  `<command>/<action>done` text protocol but Laguna was strongest with native
  tool-calling in the baseline. Whichever is chosen, filter + train + eval all use it.
- MoE route-learning (hypothesis): a small RL run on one category may route-learn
  narrow command templates instead of a general progress-state controller. Varied C1
  difficulty + the action-change reward term are the mitigations; watch held-out
  transfer to C2-C4 in v2 as the check.
- Reward-variance HARD-STOP gate runs before any GRPO/CISPO launch.
