# Adapters — binding the protocol to your tooling

**Available adapter specs:** [`buzz.md`](buzz.md) — AgentCollab over a [Buzz](https://github.com/block/buzz) Nostr relay: keypair-backed agent identity, envelopes as signed events, and a relay-enforced handshake.

The protocol core (`protocol/`) names five interfaces and never a product: **work tracker**, **session log**, **charter**, **decision record**, **ground truth**. A deployment binds them in a short *integration profile* — one markdown file, kept in the consuming project, that answers "where does each interface live here?" Agents load the profile alongside the protocol.

## Profile template

```markdown
# AgentCollab Integration Profile — <project>
**Protocol:** <output of bin/acp-id.sh> (bundle vendored at <path>; verify: bin/acp-verify.sh)

| Interface | Binding |
|---|---|
| work tracker | <e.g. GitHub Issues — open: `gh issue list`; claimed: assignee field> |
| session log | <e.g. `logs/sessions/YYYY-MM-DD_HHMMSS_<agent-id>.md`> |
| charter | <e.g. front-matter block in each agent prompt under `agents/`> |
| decision record | <e.g. `DECISIONS.md`, ADR format> |
| ground truth | <e.g. this git repository + the deployed system at <host>> |

**Handshake enforcement:** <e.g. session-start hook runs `bin/acp-verify.sh`; failures block the session>
**Local extensions:** <anything this deployment adds on top of the core — extensions may add rules, never weaken core controls D1–D6>
```

## Example bindings

- **GitHub Issues as work tracker:** claimed = issue has an assignee whose name matches an agent `id`; control D5 = `gh issue list --assignee '*'` filtered for other live agent ids before mutating.
- **Plain files as work tracker:** a `WORK.md` table with columns `item | status | claimed_by | updated`; D5 = grep for rows claimed by an id other than yours.
- **Session log as directory:** one file per session; the CONTEXT-HANDOFF envelope is the file's final section, making the latest log entry the successor's entry point.

Keep profiles boring. The interesting guarantees live in the core and the handshake; a profile that adds cleverness is a fork wearing a costume — and a fork changes the protocol ID.
