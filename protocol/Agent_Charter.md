# Agent Charter

**Purpose:** Define the minimal machine-readable block every participating agent declares — identity, specialization, write scopes, approval boundaries, and handoff obligations. The Collaboration Protocol arbitrates *between* charters; it cannot arbitrate between agents that never declared one.

**Placement:** In the agent's prompt (front-matter, immediately after the title), or in a `charters/` directory the deployment declares. Wherever it lives, it must be readable by every counterparty agent — a charter the other side cannot read fails the protocol's information-parity constraint (Collaboration Protocol §C.1).

---

## The block

```yaml
agent_charter:
  version: 1.0                    # Charter schema version (this document)
  id: content-agent-v1.0          # Stable agent id: <role>-agent-v<major>.<minor>.
                                  #   Used in envelopes, work-item claims, commits.
  specialization: >               # One sentence: the context this agent is optimized
    ...                           #   to hold. Load-bearing for delegation (§E): work
                                  #   outside it is handed to a specialist, not absorbed.
  write_scopes:                   # Path globs / surfaces this agent may create or
    - "docs/**"                   #   modify. Everything else is DELEGATE territory.
  approval:
    autonomous: [ ... ]           # Reversible actions inside write_scopes
    overseer: [ ... ]             # An authorized overseer agent may approve on a
                                  #   human's behalf. Deployments without an overseer
                                  #   treat these as `human`.
    human: [ ... ]                # Only a human may approve: destructive, outward-
                                  #   facing, or contract-changing actions.
                                  #   NEVER self-approve or reclassify downward.
  handoff:
    on_exit: context_handoff      # Publish the CONTEXT-HANDOFF envelope at close (§A)
    on_receive: inventory_first   # First output on receiving a handoff is the
                                  #   INVENTORY report, after the Handshake (§B)
```

## Field rules

| Field | Rules |
|---|---|
| `id` | Stable across sessions; the same string appears in envelopes (`From:`), work-tracker claims, and any commit/attribution trailer the deployment uses. Two live sessions sharing an `id` defeats collision detection (control D5). |
| `specialization` | The delegation trigger. If a piece of work does not fit this sentence, the protocol expects a `DELEGATE` block, not quiet absorption. |
| `write_scopes` | Interpreted against ground truth paths/surfaces. Writing outside scope requires a `DELEGATE` to the owning agent or a documented, logged takeover — never a silent edit. |
| `approval.*` | The three tiers are exhaustive; an action not listed anywhere defaults to `human`. Self-approval and downward reclassification are prohibited (Collaboration Protocol §C.1). |
| `handoff` | Both obligations are unconditional for protocol participants. |

## Enforcement honesty

The charter is declarative. Presence is checkable (`grep -l 'agent_charter:'`); adherence is instructed-only unless the deployment wires scope checks into its harness (e.g. a pre-commit hook diffing touched paths against the active agent's `write_scopes`). Write the block as if enforced — deployments that later add enforcement will read these declarations as their policy source.
