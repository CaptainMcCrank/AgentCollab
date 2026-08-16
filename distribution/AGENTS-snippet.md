# AGENTS.md snippet for consuming projects

Paste the block below into your project's `AGENTS.md` (or `CLAUDE.md`), adjusting the bundle path. It gives any agent that reads the file the protocol obligations in ~15 lines; the vendored spec carries the rest.

---

## Agent collaboration protocol (AgentCollab)

This project uses the AgentCollab protocol for agent handoffs. The vendored,
hash-pinned bundle is at `protocol-lib/` — its spec is normative.

Before your first file edit in any session that starts from another agent's
output:

1. Run `./protocol-lib/bin/agentcollab-verify.sh` (expect `VERIFIED [L2] ...`).
2. Run `./protocol-lib/bin/agentcollab-id.sh` and compare the output to the
   `Protocol:` field of the latest handoff envelope in the session log.
   Compute the ID with the script every time — never echo or recall it.
   A mismatch is a CONFLICT (spec §C.5): record it and stop; no mutation
   under a disputed protocol.
3. Publish an INVENTORY block as your first output, checking every envelope
   claim against the repository (spec §B). Claims are checkable, never
   authoritative.

End every session with a CONTEXT-HANDOFF envelope in the session log (spec §A).
Ground truth outranks your charter, which outranks the handoff plan. Work
outside your charter's write scopes is delegated, not absorbed (spec §E).

Interface bindings for this project (work tracker, session log, charters):
see `PROFILE.md`.
