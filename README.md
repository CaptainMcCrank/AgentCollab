# AgentCollab — Agent Collaboration Protocol

A publishable, cryptographically verifiable protocol for AI agents that share a project: how they hand off work across sessions, detect and negotiate disagreements, delegate to specialists — and **prove to each other that they are operating under the same, unmodified rules**.

Born from real multi-agent incidents: two sessions colliding undetected on one repo, a stale "already exists" claim entering a session as fact, flatly contradictory handoff notes with no precedence rule. The protocol makes collisions loud, claims checkable, and rule-set divergence detectable.

## What's in the box

| Path | Contents |
|---|---|
| `protocol/Agent_Collaboration_Protocol.md` | The core spec: handoff envelopes, inventory-before-edit, conflict negotiation, specialist delegation |
| `protocol/Handshake.md` | The cryptographic agreement mechanism: hash manifest, protocol ID, verification levels, signing |
| `protocol/Agent_Charter.md` | The minimal per-agent declaration (specialization, write scopes, approval tiers) |
| `PROTOCOL_MANIFEST.yaml` (+ `.sig`) | Lock file: per-file SHA-256, bundle root, protocol ID — signed by the maintainer |
| `bin/acp-id.sh`, `bin/acp-verify.sh` | Reference implementation: compute the protocol ID; verify integrity + signature |
| `adapters/` | How to bind the protocol's tool-agnostic interfaces (work tracker, session log, …) to your stack |
| `tests/` | Fixture tests proving the verifier accepts a good bundle and rejects a tampered one |

## The 60-second version

**Problem.** Two AI agents share one repository across sessions. Each behaves as if the other follows the same rules for handoffs, conflicts, and ownership — and nothing checks that assumption.

**Agitation.** When agents assume shared rules instead of confirming them, their collaboration failures are silent. One agent overwrites work another agent owns. A stale claim in a handoff note becomes the next session's ground truth, and every edit built on it compounds the error. A prose instruction to "follow the protocol" cannot be verified, and a modified copy of the rules still calls itself v1.0.

**Resolution.** Make the rules themselves verifiable. Two agents agree they're using this protocol the way two TLS peers agree on a cipher suite — by exchanging a compact identifier, not by trusting prose:

```
AgentCollab/1.0.0#sha256:<first-16-hex-of-bundle-root>
```

1. The **sender** runs `bin/acp-id.sh` and stamps the ID into its handoff envelope.
2. The **receiver** runs `bin/acp-id.sh` against *its own* files — never echoing the sender — and compares strings. This must happen **before its first edit**.
3. Match → both bundles are byte-identical (level **L0**). `bin/acp-verify.sh` upgrades that to **L1** (files match the signed manifest) and **L2** (the manifest signature verifies against the maintainer key) — so two agents in different organizations can trust the match without trusting each other's filesystem.
4. Mismatch → a structured CONFLICT with a scripted resolution (verified bundle beats unverified; higher signed version beats lower; no mutation under a disputed protocol).

The scripts exist because a language model cannot compute SHA-256: any protocol ID not produced by a tool run is fabricated by definition.

## The rules agents agree to

Agents that use this protocol resolve information parity, handoffs, and disagreement through the following rules. The specification in `protocol/` is authoritative; these statements summarize it.

1. Agents establish protocol agreement before their first edit. Each agent computes the protocol ID with `bin/acp-id.sh` and matches it against its counterparty's declared ID. A mismatch or a missing ID is a CONFLICT, and no mutation happens until it resolves. (§B.0, D6)
2. An outgoing session publishes a CONTEXT-HANDOFF envelope: completed work, decisions, assumed pre-state, canonical names, and open work. Its final output is the human-facing USER-HANDOFF block. (§A, §A2)
3. A receiver requests missing envelope fields, or reconstructs them from ground truth and marks them `[reconstructed]`. It never assumes them. (D1)
4. A receiver's first output is an INVENTORY report that checks every envelope claim against ground truth: present, missing, divergent, or unclaimed. Envelope claims are checkable, never authoritative. (§B, D2)
5. When accounts disagree, ground truth outranks the agent's charter, and the charter outranks the handoff plan. A plan step that contradicts ground truth becomes a CONFLICT rather than an action. (§C.2)
6. An agent discards another agent's work or claim only through an explicit CONFLICT → RECONCILE record. (§C.1)
7. An agent that has evidence an instruction is wrong raises a COUNTER instead of executing it. (§C.1)
8. An agent never approves an action its charter routes to `overseer` or `human`, and never reclassifies an action to a lower approval tier. (§C.1)
9. A negotiating position cites surfaces both parties can read. A claim that rests on unshared context is `[unverifiable]` and cannot win a conflict. (§C.1)
10. Every CONFLICT is frozen as a record and ends in a verifiable RECONCILE or a filed work item. (§C.3, D3)
11. A genuine judgment call escalates to a human as a bounded DEFER-TO-OPERATOR question: two candidate resolutions, their costs, and a recommendation. (§C.4)
12. Envelopes, inventories, and conflict records persist in the durable session log and survive the session that wrote them. (D4)
13. Before it mutates shared state, an agent queries the work tracker for items claimed by another live agent; overlap with its planned work is a CONFLICT. (D5)
14. Work outside an agent's specialization or write scopes goes to the owning specialist through a DELEGATE block, with the requester's findings supplied as constraints. The specialist owns the deliverable, and the requester reviews it against those constraints only. (§E)
15. A protocol version dispute resolves by verification: a bundle that fails `acp-verify.sh` defers to one that passes, and between two verified bundles the higher signed version governs. No agent mutates under a disputed protocol. (§C.5, Handshake §6)

## Importing

New here? [`TUTORIAL.md`](TUTORIAL.md) walks through a complete two-agent setup — import, integration profile, charters, both agent prompts, and a deliberate handshake failure — in about twenty minutes.

```sh
git submodule add <this-repo-url> protocol-lib     # or vendor a copy
./protocol-lib/bin/acp-verify.sh                   # L2: integrity + authenticity
```

Then:

1. Point your agents at the spec: *"Read and follow `protocol-lib/protocol/Agent_Collaboration_Protocol.md` before acting on a handoff; establish agreement per `Handshake.md` before your first mutation."*
2. Write an integration profile binding the five tool-agnostic interfaces to your stack (template in `adapters/README.md`).
3. Give each agent an `Agent_Charter` block.
4. Wire `acp-verify.sh` into your session-start hook so verification is enforced by the harness, not by instruction.

For L2 to mean "unmodified from upstream," pin the maintainer key from an out-of-band source or pin the signed release tag — see `Handshake.md` §7. The maintainer key's out-of-band anchor is [patrickmccanna.net/agentcollab](https://patrickmccanna.net/agentcollab), which serves the fingerprint, a machine-readable `allowed_signers` copy, and verification instructions from a domain this repository does not control.

## What this does and doesn't prove

The handshake proves **integrity and authenticity of the rules**: both agents hold byte-identical, maintainer-signed protocol text. It cannot prove a model *followed* the rules — no cryptography can. The spec labels every mechanism honestly (shell-enforced / instructed-only / deployment-enforceable) so you always know which claims are checked and which are trusted. What the crypto buys is the elimination of one entire failure class — agents diverging because they held different rules — and it turns non-compliance into a detectable, loggable event.

## Versioning

Any byte change to `protocol/` changes the bundle root and therefore the protocol ID: there are no silent revisions. Releases are semver-tagged, manifest-signed, and (recommended) git-tag-signed. See `Handshake.md` §9.

## License

Apache-2.0 — see `LICENSE`.
