# AgentCollab Integration Profile — conformance workspace
Protocol: run ./protocol-lib/bin/agentcollab-id.sh (never recall an ID from memory)

| Interface | Binding |
|---|---|
| work tracker | `WORK.md` table in the workspace root |
| session log | `logs/`, one markdown file per session |
| charter | `charters/`, one file per agent |
| decision record | `DECISIONS.md` |
| ground truth | this workspace's files |

**Handshake enforcement:** run `./protocol-lib/bin/agentcollab-verify.sh` before any edit.
