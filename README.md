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

Two agents agree they're using this protocol the way two TLS peers agree on a cipher suite — by exchanging a compact identifier, not by trusting prose:

```
AgentCollab/1.0.0#sha256:<first-16-hex-of-bundle-root>
```

1. The **sender** runs `bin/acp-id.sh` and stamps the ID into its handoff envelope.
2. The **receiver** runs `bin/acp-id.sh` against *its own* files — never echoing the sender — and compares strings. This must happen **before its first edit**.
3. Match → both bundles are byte-identical (level **L0**). `bin/acp-verify.sh` upgrades that to **L1** (files match the signed manifest) and **L2** (the manifest signature verifies against the maintainer key) — so two agents in different organizations can trust the match without trusting each other's filesystem.
4. Mismatch → a structured CONFLICT with a scripted resolution (verified bundle beats unverified; higher signed version beats lower; no mutation under a disputed protocol).

The scripts exist because a language model cannot compute SHA-256: any protocol ID not produced by a tool run is fabricated by definition.

## The rules agents agree to

The spec is normative; this is the digest. An agent operating under this protocol commits to the following, in the order they bite during a session:

1. **Handshake before mutation.** Compute the protocol ID with `bin/acp-id.sh` and match it against your counterparty's declared ID. A mismatch or a missing ID is a CONFLICT; nothing is edited until it resolves. (§B.0, control D6)
2. **Publish an envelope on exit.** An outgoing session ends with a CONTEXT-HANDOFF envelope — what it did, decisions, assumed pre-state, canonical names, open work — followed by a human-facing USER-HANDOFF block as its true last output. (§A, §A2)
3. **Never assume missing fields.** A receiver handed an incomplete envelope requests the missing fields or reconstructs them from ground truth and marks them `[reconstructed]`. (D1)
4. **Inventory before any edit.** The receiver's first output is an INVENTORY report checking every envelope claim against ground truth: present, missing, divergent, unclaimed. Handoff claims are checkable, not authoritative. (§B, D2)
5. **Precedence when accounts disagree:** ground truth beats the agent's charter, which beats the handoff plan. A plan step contradicting ground truth becomes a CONFLICT, not an action. (§C.2)
6. **No silent override.** Another agent's work or claim is never discarded without an explicit CONFLICT → RECONCILE record. (§C.1)
7. **No silent obedience.** An instruction you have evidence is wrong is never executed as written; raise a COUNTER. (§C.1)
8. **No self-approval.** An agent never approves an action its charter routes to `overseer` or `human`, and never reclassifies an action to a lower tier. (§C.1)
9. **Information parity.** A negotiating position must cite surfaces both parties can read; a claim resting on unshared context is `[unverifiable]` and cannot win a conflict. (§C.1)
10. **Conflicts do not evaporate.** Every CONFLICT is frozen as a record and ends in exactly one of: a verifiable RECONCILE, or a filed work item deferring it. (§C.3, D3)
11. **Escalations are bounded.** A genuine judgment call goes to a human as DEFER-TO-OPERATOR with two resolutions, their costs, and a recommendation — never an open-ended "what should I do?". (§C.4)
12. **Records persist.** Envelopes, inventories, and conflict records are written to the durable session log, recoverable outside any LLM session. (D4)
13. **Check for concurrent sessions.** Before mutating, query the work tracker for items claimed by another live agent id; overlap with your planned work is a CONFLICT. (D5)
14. **Delegate outside your specialization.** Work beyond your charter's specialization or write scopes goes to the owning specialist via DELEGATE, with your findings supplied as constraints. The specialist owns the deliverable; the requester reviews against constraints only. (§E)
15. **Version disputes resolve by verification.** In a protocol ID mismatch, a bundle that fails `acp-verify.sh` defers to one that passes; between two verified bundles, the higher signed version governs; anything murkier escalates. No mutation happens under a disputed protocol. (§C.5, Handshake §6)

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
