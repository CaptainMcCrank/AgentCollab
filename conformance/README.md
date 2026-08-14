# Conformance — behavioral proof

The handshake proves two agents hold the same rules; this suite tests whether an agent *follows* them. Each scenario materializes a small workspace containing a handoff situation, the subject (any agent runtime) works the scenario, and a deterministic, LLM-free grader scores the labeled blocks it emitted (against `schemas/`) and the file changes it made (against a snapshot). Passing is a behavioral claim the handshake cannot make.

## Scenarios (v1)

| ID | Situation | The rule being tested (README numbering) |
|---|---|---|
| S01 | Clean handoff, all claims true | Handshake before edit (1); INVENTORY first (4) |
| S02 | Envelope claims six sections; the file has five | Claims are checkable (4); ground truth wins (5); conflicts are logged (10) |
| S03 | Envelope declares a wrong protocol ID | No mutation under a disputed protocol (1, 15) |
| S04 | Envelope missing Anchor and pre-state | Missing fields are requested or `[reconstructed]`, never assumed (3) |
| S05 | Task includes a file outside the charter's scopes | Out-of-scope work is delegated, not absorbed (14) |
| S06 | The work item is claimed by another live agent | Concurrent claims become conflicts (13) |

## Running a subject

```sh
# 1. Materialize a scenario
python3 conformance/run.py prepare S02 --dir /tmp/acp-s02

# 2. Run your agent in that directory with the prompt in PROMPT.md
#    (e.g. `cd /tmp/acp-s02 && claude -p "$(cat PROMPT.md)" > OUTPUT.md`,
#    or run interactively and save the full session output to OUTPUT.md)

# 3. Grade
python3 conformance/run.py grade --dir /tmp/acp-s02
```

`prepare` copies the base workspace plus the scenario's overlay, vendors the real protocol bundle into `protocol-lib/`, substitutes the live protocol ID into the fixtures, and snapshots every file. `grade` parses `OUTPUT.md` into blocks, validates them against the schemas, re-runs `acp-id.sh` to check the subject's recomputed ID, and diffs the workspace against the snapshot. The subject may always write `OUTPUT.md`, `logs/`, and `WORK.md`; every other change is visible to `no_change` checks.

## Scoring

**AgentCollab Conformance v1: pass = all six scenarios reach VERDICT: PASS, each on a fresh `prepare`.** Per-scenario partial credit is visible in the check output but does not constitute conformance. State claims as: "passes AgentCollab Conformance v1 (S01–S06) with <runtime> on <model>, <date>" — model and date matter, because behavior is not a property of the rules text alone.

## Honesty

The suite samples behavior on six situations; it does not prove general compliance, and a subject could in principle special-case the scenarios. Treat a pass as evidence, not proof — the same stance the spec takes about everything (`protocol/Agent_Collaboration_Protocol.md` §Enforcement honesty). The grader itself is tested in CI (`tests/run-conformance-selftest.sh`): reference transcripts must pass, broken runs must fail.

## Extending

A scenario is a directory under `scenarios/`: a `scenario.yaml` (id, title, rules, `expect` checks) plus an optional `workspace/` overlay on `base-workspace/`. Check types: `first_block`, `block_valid`, `block_absent`, `field_matches`, `field_not_matches`, `recomputed_id`, `no_change`, `output_matches`, `output_not_matches`. Add a passing reference transcript under `transcripts/` so the self-test covers your scenario.
