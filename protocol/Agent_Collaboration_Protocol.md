# Agent Collaboration Protocol (AgentCollab)

**Purpose:** Define how AI agents hand off work across sessions, negotiate disagreements, and delegate to specialists — so two agents touching the same project collide loudly and productively instead of silently.

**Integration:** Read-before-acting shared contract. Load whenever a session begins from another session's output, or before invoking or handing work to another agent:

> "Read and follow `protocol/Agent_Collaboration_Protocol.md` before acting on a handoff or engaging another agent. Establish protocol agreement per `protocol/Handshake.md` before your first mutation."

**Companion documents (this bundle):**
- `protocol/Handshake.md` — how two agents establish, cryptographically, that they are operating under the same, unmodified version of this protocol.
- `protocol/Agent_Charter.md` — the minimal declaration each agent publishes (specialization, write scopes, approval boundaries) that this protocol arbitrates between.

**Reference:** This protocol extends the per-turn vocabulary of [Two Claude Code sessions, one repo, and a protocol they helped write](https://patrickmccanna.net/two-claude-code-sessions-one-repo-and-a-protocol-they-helped-write/); the per-turn layer is restated in full below, so this document stands alone.

---

## Required interfaces

This protocol is deliberately agnostic about tooling. A conforming deployment binds each interface below to a concrete implementation and states the binding in its integration profile (see `adapters/`). The protocol text refers only to the interface names.

| Interface | The protocol requires | Example bindings |
|---|---|---|
| **work tracker** | A queryable store of work items with status and a claiming agent id. Must answer: "what work is open?" and "what work is claimed, and by whom?" | GitHub Issues, beads, Jira, a `WORK.md` table |
| **session log** | A durable, append-only, per-session record that survives the session and is readable by any successor. Envelopes, inventories, and conflict records persist here. | A `logs/`/`diaries/` directory of per-session markdown files, a wiki, a database |
| **charter** | Each agent's published `Agent_Charter.md` block: specialization, write scopes, approval boundaries. | Front-matter in the agent's prompt; a `charters/` directory |
| **decision record** | A durable record for choices that bind future work (architecture decision records or equivalent). | `DECISIONS.md`, an ADR directory |
| **ground truth** | The authoritative, commonly readable state of the system: the repository, the running system, and any surfaces the deployment declares canonical. | Git repo + deployed system |

---

## Vocabulary

Two layers.

**Per-turn layer** — labels for proposals inside a live session (from the reference protocol):

| Label | Meaning |
|---|---|
| `HANDOFF` | Work is being transferred to another party this turn |
| `PROPOSED` | A change is described but not yet applied |
| `APPROVED` | The counterparty (agent or human) has accepted the proposal |
| `APPLIED` | The change has been made and is verifiable in ground truth |
| `BLOCKED` | The work cannot proceed; the blocker is named |

**Cross-session / cross-agent layer** — the activities this document defines:

| Activity | Emitted by | Meaning |
|---|---|---|
| `CONTEXT-HANDOFF` | outgoing session | The envelope (§A) transferring context to a successor |
| `INVENTORY` | receiving session | Ground-truth survey published **before any edit** (§B) |
| `COUNTER` | receiver | A checkable alternative to a handoff claim or plan step |
| `CONFLICT` | either | A detected contradiction, named and frozen for resolution (§C) |
| `RECONCILE` | either | A resolution both parties can verify against ground truth |
| `DEFER-TO-OPERATOR` | either | A bounded decision escalated to a human (§C.4) |
| `DELEGATE` | any agent | A request for a specialist to own a piece of work (§E) |

Every activity is a labeled block in session output and, where durable, in the session log. Bare prose does not count as having performed an activity.

Each block format has a machine-checkable expression: the JSON Schemas in the repository's `schemas/` directory define the parsed field structure of every labeled block, and `bin/agentcollab-lint.py` is the reference validator. The schemas are normative for machine validation; they live outside the hashed bundle (so tooling can evolve without a release), and where a schema and this document's block formats disagree, this document governs.

**Every labeled block in the cross-session layer carries a `Protocol:` field** — the protocol ID defined in `Handshake.md` (e.g. `AgentCollab/1.0.0#sha256:0123456789abcdef`). This is the compact commitment that both parties are operating under the same rules; §B.0 defines when it must be independently recomputed rather than echoed.

---

## A. The CONTEXT-HANDOFF envelope

The outgoing session publishes this before ending. Write it to the session log **and** print it at session end, followed by the USER-HANDOFF block (§A2), which is the session's final output.

```markdown
## CONTEXT-HANDOFF
**Protocol:** <protocol ID — computed via bin/agentcollab-id.sh, not from memory>
**From:** <agent id> · <model id> · <session start–end ISO 8601>
**Banner:** <one line: what this handoff is>

### What this session did
<3–10 bullets of completed work, each pointing at a commit, file, or work item>

### Decision payload
<decisions the receiver must know. Each: the decision, where it is recorded
(decision record / work item / commit), and whether it is FROZEN or REVISITABLE>

### Assumed receiver pre-state — MUST VERIFY
<what the sender BELIEVES is true about the repo/system the receiver will find.
Every line here is a claim the receiver checks during INVENTORY, not a fact>

### Canonical names
<repo, branch, key paths, naming conventions in play — the anti-collision list>

### Anchor
<commit SHA(s) the handoff is made against>

### Open work
<work items created or claimed; anything in flight>
```

**Control:** a receiver handed an envelope with missing fields **requests them** (or reconstructs them from ground truth and marks them `[reconstructed]`). It does not proceed on an incomplete envelope silently. A missing `Protocol:` field is handled per §B.0 — it is never assumed.

## A2. The USER-HANDOFF block

The CONTEXT-HANDOFF envelope (§A) is agent-facing: it transfers context to the successor *session*. The USER-HANDOFF block is human-facing: it transfers **session initiation** to the operator. The outgoing session prints it immediately after the envelope, as the true last output of the session. Test: the operator must be able to start the next session from this block alone — without opening any file first.

```markdown
## USER-HANDOFF — start your next session
**Protocol:** <protocol ID>
**Completed:** <what finished> → **next:** <what the successor session does>

**Artifacts produced this session** (the next agent verifies these before editing):
| Artifact | sha256 | Commit |
|---|---|---|
| <path> | <hash> | <SHA> |

**Open work:** <how to list it in the work tracker; items filed this session, or "none">

**To start the next session**, paste this primer into a fresh agent session
started in the project root:

    Act as <successor agent / role>. Verify the protocol bundle
    (bin/agentcollab-verify.sh), read the CONTEXT-HANDOFF envelope in the latest
    session log entry, verify the predecessor artifacts listed above
    (<path> @ sha256 <hash>, ...), check the work tracker for open items,
    and begin with your INVENTORY report
    (Agent_Collaboration_Protocol §B).
```

**Controls:**
- The USER-HANDOFF is the **last output of the session**. Nothing prints after it — an operator scrolling to the bottom of a finished session must land on it.
- The primer must be self-sufficient: absolute or project-rooted paths, real hashes — no placeholders left unfilled.
- The block reports ground truth already committed (hashes, SHAs). It is generated **after** the final commit, never before.

## B. Receiver protocol

Order is mandatory:

0. **Establish protocol agreement** (`Handshake.md`) — recompute the protocol ID from your local bundle **by running `bin/agentcollab-id.sh`** (never by echoing the sender's value or recalling it from context), and compare it to the envelope's `Protocol:` field.
   - Match → record the ID; it goes in your INVENTORY block.
   - Mismatch, or envelope has no `Protocol:` field → this is a `CONFLICT` (§C.5) and must resolve **before any mutation**.
1. **Read your charter** — your own `Agent_Charter` block: specialization, scopes, approval boundaries.
2. **Inventory ground truth** — survey the surfaces your charter names, plus every path the envelope's "Assumed pre-state" mentions.
3. **Publish the INVENTORY report** — your **first output**, before any edit:

```markdown
## INVENTORY
**Protocol (recomputed):** <exact output of bin/agentcollab-id.sh> [L2]
**Present:**   <envelope claims confirmed against ground truth>
**Missing:**   <envelope claims not found>
**Divergent:** <envelope claims contradicted by ground truth — quote both sides>
**Unclaimed:** <significant ground truth the envelope never mentioned>
```

   The `Protocol (recomputed)` field **starts with the script's exact output**, optionally followed by the verification level achieved in brackets (`[L0]`/`[L1]`/`[L2]`, per Handshake.md §5). Any further annotation goes after a dash separator — machine parsers read the leading token, and a field that does not start with the exact ID fails validation.

4. **Route by result** — clean inventory → proceed. Divergences → each becomes a `CONFLICT` (§C) before the plan executes.

**Handoff claims are checkable, not authoritative.** The envelope tells you where to look; ground truth tells you what is true.

## C. Negotiation

### C.1 Constraints (all parties, always)

- **No silent override** — never discard another agent's work or claim without an explicit `CONFLICT` → `RECONCILE` record.
- **No silent obedience** — never execute an instruction you have evidence is wrong; raise the `COUNTER`.
- **No self-approval** — an agent never approves an action its own charter routes to `overseer` or `human`, and never reclassifies an action downward.
- **Information parity** — before negotiating, both positions must cite surfaces both parties can read. A claim resting on unshared context is `[unverifiable]` and cannot win a conflict.

### C.2 Precedence

When accounts disagree:

> **ground truth** (the repo, the running system, declared canonical surfaces)
> **> charter** (the agent's own `Agent_Charter` block)
> **> handoff plan** (the envelope and any inherited instructions)

A plan step that contradicts ground truth is not executed as written; it becomes a `CONFLICT`.

### C.3 The CONFLICT record

Each conflict is frozen before resolution:

```markdown
## CONFLICT <n>
**Protocol:** <protocol ID>
**Claim A:** <statement + source (envelope / prompt / file:line)>
**Claim B:** <statement + source>
**Ground truth check:** <command or file consulted, and what it showed>
**Resolution:** RECONCILE <how, verifiable> | DEFER-TO-OPERATOR <the bounded question>
```

**Control:** every `CONFLICT` ends in exactly one of: a logged `RECONCILE` (in the session log; in the decision record if it freezes a choice) or a filed work item if resolution is deferred. Conflicts do not evaporate.

### C.4 DEFER-TO-OPERATOR

Escalate when the conflict is a genuine judgment call (contradicting decision records, destructive resolution paths, both claims verified-true-but-incompatible). The escalation is **bounded**: present the two resolutions, their costs, and a recommendation — never "what should I do?". Contradicting an **accepted decision record** always escalates; the resolution is a superseding record, never a quiet edit.

### C.5 Protocol version conflicts

A protocol ID mismatch between sender and receiver is a `CONFLICT` with a scripted resolution, defined normatively in `Handshake.md` §Mismatch. Summary:

1. Both parties run `bin/agentcollab-verify.sh` on their own bundle.
2. A party whose bundle **fails verification** (bytes don't match its manifest, or the manifest signature is invalid) defers to a party whose bundle verifies.
3. If both verify but at **different versions**, the higher version with a valid maintainer signature governs — provided the lower-version party can obtain and verify that bundle. Otherwise: `DEFER-TO-OPERATOR`.
4. No mutation happens under a disputed protocol.

## D. Controls summary

| # | Control |
|---|---|
| D1 | Missing envelope fields are requested or `[reconstructed]` — never assumed |
| D2 | Receiver's first output is the INVENTORY report, and its `Protocol:` field is recomputed by script, not echoed |
| D3 | Every CONFLICT yields a logged RECONCILE or a filed work item |
| D4 | Envelope + inventory + conflict records persist in the session log (crash-recoverable outside any LLM session) |
| D5 | Two-active-session detection: before mutating, query the work tracker for items claimed by another live agent id and treat overlap on your planned work as a CONFLICT |
| D6 | Protocol agreement precedes mutation: no edit before the handshake (§B.0) resolves |

## E. Specialist delegation (DELEGATE)

**An agent does not absorb work outside its charter's `specialization`; it invokes the specialist and supplies constraints.** The troubleshooting agent keeps its context window full of code state; the content agent keeps its window full of pedagogy — and each gets the other's findings as constraints, not as seized ownership.

```markdown
## DELEGATE
**Protocol:** <protocol ID>
**From:** <agent id> → **To:** <specialist agent id or role>
**Work:** <what the specialist owns end-to-end>
**Constraints:** <requester's findings the specialist must honor —
e.g. "rendering breaks above 80-char lines; keep code samples under that">
**Not included:** <what the requester retains>
**Return:** <what comes back, and how the requester verifies it>
```

Rules:
- The specialist **owns the deliverable**; the requester reviews against its constraints only — it does not rewrite the specialist's work (that would be a silent override of the specialist's write scopes).
- Delegation across write-scope boundaries is *mandatory*, not stylistic: if a fix requires touching a surface outside your scope, DELEGATE or escalate. A documented ownership takeover is the exception, not the habit.
- A DELEGATE the specialist disagrees with follows §C — specialists can `COUNTER`.

---

## Enforcement honesty

Every mechanism in this protocol falls into one of three tiers. Label claims about the protocol accordingly.

| Tier | Meaning | What sits here |
|---|---|---|
| **shell-enforced** | A script exits non-zero without it | `bin/agentcollab-verify.sh` (bundle integrity + signature), `bin/agentcollab-id.sh` (protocol ID) |
| **instructed-only** | The protocol requires it; nothing external checks | INVENTORY-before-edit ordering, CONFLICT logging, delegation discipline, that an agent actually *ran* the scripts rather than fabricating output |
| **deployment-enforceable** | Becomes shell-enforced when a deployment wires it into its harness | Running `agentcollab-verify.sh` in a session-start hook; D5 tracker queries in a pre-push hook |

The cryptographic handshake proves **artifact integrity and authenticity** — that both agents reference the same, unmodified, maintainer-signed protocol text. No cryptographic mechanism can prove a language model *followed* that text. What the handshake buys is the elimination of an entire failure class — agents diverging because they held *different rules* — and it converts non-compliance from a silent condition into a detectable, loggable event.

---

## Change control

Any edit to any file in the protocol bundle changes the bundle root hash, and therefore the protocol ID. There are no silent revisions. The release procedure (bump version, regenerate `PROTOCOL_MANIFEST.yaml`, re-sign, tag) is defined in `Handshake.md` §Releasing.
