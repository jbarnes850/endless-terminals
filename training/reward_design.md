# Reward Design

## Cleanest Executable Reward

Use a hidden final-verifier reward as the anchor, plus small process shaping that is potential-based and state-derived. The reward should train meta-control and adjacent capability expression without making public tests, checkpoint labels, or task metadata into the target.

Recommended MVP scalar now implemented in `environments/meta_control`:

```text
R =
  1.00 * harbor_reward
+ [0.00, 0.30] gated_progress
+ [-0.20, +0.20] stop_quality
- [0.00, 0.17] nonprogress_penalty
- [0.00, 0.10] malformed_tool_penalty
- [0.00, 0.02] turn_cost
```

Keep weights conservative. Final hidden-verifier success stays dominant; process terms only make loop/stop behavior visible to RL.

## Optimizer/Advantage Stance

Use Prime-RL's native async trainer for the overnight run. The scientific claim is Laguna meta-control and generalized terminal-agent capability, not faithful reproduction of a trainer objective. Keep the Dr. GRPO-informed hygiene that matters for this reward shape:

- `rollouts_per_example = 16` for stable group comparisons.
- Default group mean-baseline advantage.
- No per-group reward-std normalization.
- No length shaping / GR3 rescaling.
- Native Prime-RL default trainer loss, with conservative LR and killable runs.

## Components

`final_success`

- Binary hidden final verifier result, implemented by Harbor's `harbor_reward`.
- Must be the dominant reward term.
- Must execute after the rollout ends or the stop action.

`delta_hidden_assertion_fraction`

- Longest-prefix checkpoint shaping from hidden pytest execution order.
- Do not expose assertion names, checkpoint order, or descriptions to the policy.
- Later assertions do not count unless all earlier checkpoints pass.
- Status: implemented as `gated_progress` from verifier-emitted `__ET_CHECKPOINTS__` metadata in Harbor stdout. This is final-state prefix progress, not per-turn filesystem potential.

`stop_quality`

- Positive when the agent stops after hidden final success.
- Negative when it stops before final success.
- Negative when it continues after the task is already complete.
- This term directly targets the observed premature-stop and run-past-complete failures.

`stall_or_repeat_penalty`

- Penalizes adjacent identical tool actions and high dominant-action share.
- Capped tightly so correct repeated checks are not more important than final success.
- Status: implemented as `nonprogress_penalty`; unchanged-filesystem detection remains an escape-trace gate until per-turn state fingerprints are emitted.

`malformed_tool_penalty`

- Small penalty for tool/runtime error messages in the trajectory.
- This follows the Laguna-style principle of keeping format/tool penalties negative and small.

`turn_cost`

- Mild capped length penalty.
- This prevents cheap run-past-complete inflation but is too small to make premature stopping attractive.

`integrity_penalty`

- Fail closed on hidden verifier tampering, deletion of required files, disabling tests, network exfiltration when disallowed, or attempts to inspect private solution material.
- This should usually terminate the rollout.
- Status: not implemented as scalar reward. Harbor already returns zero on verifier failure; explicit integrity classification belongs in the escape-trace gate before it becomes a train-time penalty.

## Implemented Metrics

The wrapper logs:

- `tool_call_count`
- `unique_action_count`
- `adjacent_repeat_count`
- `dominant_action_share`
- `unchanged_state_rate` (same action plus same tool observation proxy, not true filesystem diff)
- `natural_stop`
- `max_turn_stop`
- `checkpoint_count`
- `checkpoint_prefix_share`
- `tool_error_count`
- `reward_group_std`
- `low_reward_variance_group`

The hard stop remains: if more than 50% of rollout groups have `low_reward_variance_group=1`, do not scale the run.

## Non-Reward Metrics

Log these as diagnostics first; promote to reward only if they are needed and not hackable:

- Loop rate.
- Near-identical command rate.
- Action diversity per task.
- Verifier invocation count.
- Best-seen potential versus final potential.
- Stop-early count.
- Run-past-complete count.
- No-progress turn count.
- Time-to-first-meaningful-verification.
- Pivot-after-failed-verification rate.

## Behavioral Grounding

Latest TBLite Laguna evidence should shape the task distribution and diagnostics:

- Repeated command and command-loop failures.
- Treating `exit_code=0` as success without checking the deliverable.
- Weak verification after edits.
- Premature stopping after one or two turns.
- Failure to pivot after evidence falsifies the current local plan.
- Server/API and data-artifact tasks where final state matters more than one command succeeding.

Long-horizon behavior analysis adds the same control target at larger scale:

- Ledger opacity.
- Re-entering rejected strategy families.
- Treating correctness-pass as semantic proof.
- Metric confusion.
- Thin final accounting for rejected candidates.

The reward must therefore couple recognition to changed action and completion evidence to stopping. It should not reward fluent explanations, raw command volume, or public-test repetition.

## Main Reward-Hacking Path

The most likely hack is partial-credit farming: repeatedly making shallow changes or rerunning visible checks that satisfy easy hidden assertions while avoiding the harder final deliverable. Harden against this by:

- Making final success dominate.
- Rewarding only positive potential deltas, not absolute checkpoint count every turn.
- Freezing potential credit after repeated no-progress verification.
- Gating later assertions behind prerequisite phases.
- Penalizing unchanged-state repeated actions.
- Auditing best-seen potential versus final success during escape-trace review.
