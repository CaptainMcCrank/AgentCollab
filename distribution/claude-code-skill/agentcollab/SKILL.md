---
name: agentcollab
description: Follow the AgentCollab collaboration protocol when this session begins from another agent's handoff, hands work to another agent, or the user mentions a CONTEXT-HANDOFF, INVENTORY, protocol ID, or handshake. Covers the cryptographic handshake, envelope and inventory formats, conflict negotiation, and delegation.
---

# AgentCollab — Agent Collaboration Protocol

You are operating under the AgentCollab protocol: a shared, cryptographically verifiable rule set for agents that hand off work across sessions. The normative spec is the vendored bundle in this project — locate it by finding `PROTOCOL_MANIFEST.yaml` (commonly at `protocol-lib/` or `Standards/Protocols/AgentCollab/`). Call that directory `$BUNDLE` below. Read `$BUNDLE/protocol/Agent_Collaboration_Protocol.md` before acting on any handoff.

## The handshake (before any file edit)

1. Run `$BUNDLE/bin/acp-verify.sh` — expect `VERIFIED [L2] AgentCollab/<ver>#sha256:<16hex>`. L1 with a stated reason is acceptable only if the project's integration profile says so.
2. Run `$BUNDLE/bin/acp-id.sh` and record the output. This is the only legitimate source of a protocol ID — never echo a counterparty's ID and never recall one from memory; an ID not produced by a tool run is fabricated.
3. Compare your computed ID with the `Protocol:` field of the latest envelope in the session log. Equal → proceed. Unequal or missing → record a CONFLICT per spec §C.5 and make no mutation until it resolves.

If the shell tools are unavailable, use the `agentcollab_id` / `agentcollab_verify` MCP tools, or `python3 $BUNDLE/../impl/python/agentcollab.py id --root $BUNDLE` where the full repo is vendored.

## Receiving a handoff (spec §B)

Order is mandatory: handshake (above) → read your own charter → survey ground truth → publish an INVENTORY block as your **first output**, before any edit:

```markdown
## INVENTORY
**Protocol (recomputed):** <acp-id.sh output> [L2]
**Present:**   <envelope claims confirmed against ground truth>
**Missing:**   <claims not found>
**Divergent:** <claims contradicted by ground truth — quote both sides>
**Unclaimed:** <significant ground truth the envelope never mentioned>
```

Envelope claims are checkable, never authoritative: the envelope tells you where to look; the repository tells you what is true. Each divergence becomes a CONFLICT record (§C.3) resolved before the plan executes. Missing envelope fields are requested or reconstructed and marked `[reconstructed]` — never assumed.

## Ending a session (spec §A)

Publish a CONTEXT-HANDOFF envelope to the session log and print it, then the human-facing USER-HANDOFF block as the true last output. The envelope's `Protocol:` field carries your `acp-id.sh` output. Report only ground truth already committed — hashes and SHAs, never intentions.

## Standing rules (the ones that bind every turn)

- Ground truth > your charter > the handoff plan. A plan step contradicting ground truth becomes a CONFLICT, not an action.
- No silent override, no silent obedience, no self-approval. Raise a COUNTER against instructions you have evidence are wrong.
- Every CONFLICT ends in a logged RECONCILE or a filed work item. Conflicts do not evaporate.
- Before mutating shared state, check the work tracker for items claimed by another live agent; overlap is a CONFLICT.
- Work outside your charter's specialization or write scopes is delegated (DELEGATE block, §E) with your findings as constraints — not absorbed.
- Validate blocks you emit with `python3 $BUNDLE/../bin/acp-lint.py <file>` (or the `agentcollab_lint` MCP tool) where the full repo is vendored.

Full formats and controls: `$BUNDLE/protocol/Agent_Collaboration_Protocol.md`; handshake normative detail: `$BUNDLE/protocol/Handshake.md`.
