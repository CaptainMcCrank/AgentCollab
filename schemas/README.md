# Schemas — machine-checkable protocol blocks

Standard JSON Schema (draft 2020-12) for every labeled block the protocol defines. The blocks themselves stay markdown — agents emit and read the formats in `protocol/Agent_Collaboration_Protocol.md` unchanged. These schemas define the **parsed form**: the field structure a validating harness extracts from a block before checking it.

| Block | Spec | Schema |
|---|---|---|
| CONTEXT-HANDOFF | §A | `context-handoff.schema.json` |
| USER-HANDOFF | §A2 | `user-handoff.schema.json` |
| INVENTORY | §B | `inventory.schema.json` |
| CONFLICT | §C.3 | `conflict.schema.json` |
| DELEGATE | §E | `delegate.schema.json` |
| `agent_charter` | Agent_Charter.md | `agent-charter.schema.json` |

## Parsing conventions

`bin/acp-lint.py` is the reference parser and validator. The mapping it implements:

- A block starts at its `## NAME` heading (a trailing counter or subtitle is allowed, as in `## CONFLICT 1`).
- `**Field:** value` lines become string properties; the field name is lowercased with non-alphanumerics collapsed to `_` (so `**Protocol (recomputed):**` → `protocol_recomputed`). Continuation lines append to the preceding field.
- `### Section` headings inside the envelope become arrays of their non-empty lines; decorative suffixes after an em dash are dropped from the key (`### Assumed receiver pre-state — MUST VERIFY` → `assumed_receiver_pre_state`).
- The DELEGATE `**From:** a → **To:** b` line splits into `from` and `to`.
- The USER-HANDOFF artifact table becomes an `artifacts` array of `{artifact, sha256, commit}` rows; the primer text after `**To start the next session**` becomes `primer`.
- The `agent_charter` block is YAML (bare or inside a ```yaml fence); its `agent_charter:` mapping is the instance. The optional `pubkey` field is the identity binding used by transport adapters (see `adapters/buzz.md`).

## Validation

```sh
python3 bin/acp-lint.py path/to/session-log-entry.md    # validate all blocks found
python3 bin/acp-lint.py --json file.md                  # also print the parsed JSON
```

The linter needs only the Python standard library (PyYAML for charters). The schemas are ordinary JSON Schema, so external harnesses can use any standard validator; the linter's built-in checker covers the subset these schemas use: `type`, `required`, `properties`, `items`, `enum`, `pattern`, `minItems`, `minLength`.

## Status

The schemas ship as tooling and are exercised by `tests/run-schema-tests.sh` (valid fixtures must pass, invalid must fail — see `tests/fixtures/`). They become normative — referenced from the spec — in the next bundle release (see `ROADMAP.md` item 1).
