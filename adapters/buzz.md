# Buzz Adapter — AgentCollab over a Nostr Relay Workspace

**Status:** design specification. Publishable and reviewable now; the workflow implementation and worked demo are gated on a running [Buzz](https://github.com/block/buzz) deployment.

**Scope:** an *optional* transport-and-identity binding. The AgentCollab core stays transport-agnostic; nothing in this adapter changes the hashed bundle or the protocol ID. A deployment that adopts this binding declares it in its integration profile (`adapters/README.md`).

**Terminology caution:** Buzz ships `buzz-acp`, its harness for the *Agent Communication Protocol* (the agent-harness protocol spoken by Goose, Codex, and Claude Code). That is unrelated to this protocol. This document always spells out **AgentCollab** and never abbreviates it, and integrators should do the same in Buzz-adjacent contexts.

---

## Why bind to Buzz

Buzz is a self-hostable workspace built on Nostr: every message, reaction, patch, and approval is a Schnorr-signed event in one relay log, humans and agents participate under the same kind of keypair (NIP-42 authentication), git activity lands in the same log as NIP-34 events, and a hash-chained audit service covers the sequence. That supplies, as infrastructure, the three properties the core protocol cannot provide on its own:

| Gap in the core | What Buzz provides |
|---|---|
| `From:` is self-asserted; envelopes and records are unsigned | Every event is signed by its author's key, authenticated by the relay before it flows |
| Publication-as-transport assumes a shared repo and turn-taking; cross-host ordering is undefined | The relay is a live, ordered, cross-host event log with presence |
| Handshake enforcement is per-session and honor-based | A relay workflow can check a protocol-ID tag on *every event*, continuously |

## Interface bindings

| AgentCollab interface | Buzz binding |
|---|---|
| session log | Signed events in the project's channel (event kinds below). The relay log plus `buzz-audit`'s hash chain replaces file-based session logs; control D4's durability requirement is met by the relay's persistence. |
| work tracker | Claim and status events in the project channel (or NIP-34 issue events where the deployment uses them). "Claimed by whom" is answered by event author pubkey, which is stronger than a name in a table. |
| charter | A charter event per agent (replaceable, keyed by agent id) containing the `agent_charter` block **plus one new field: `pubkey`** — the agent's Nostr public key. The binding between agent id and key is the charter; an event whose author pubkey does not match the charter's declared pubkey for that agent id fails identity verification regardless of what its `From:` field claims. |
| decision record | A decision event per record, or the repository's `DECISIONS.md` with the commit referenced from the event log — deployment's choice; declare it in the profile. |
| ground truth | The git repository **plus its NIP-34 event stream on the same relay**. Envelope claims can cite patch-event ids, putting the claim and its evidence in one searchable, signed log. |

## Event mapping

Nostr events carry arbitrary kinds and tags. Proposed kinds (provisional — deployments configure the actual numbers until a range is registered; the *structure* is the normative part):

| Protocol activity | Kind (provisional) | Content | Required tags |
|---|---|---|---|
| CONTEXT-HANDOFF | 4501 | The envelope, verbatim markdown (spec §A) | `agentcollab`, `agent`, `anchor` |
| INVENTORY | 4502 | The report, verbatim markdown (§B) | `agentcollab`, `agent`, `e` → envelope event |
| CONFLICT / RECONCILE | 4503 | The record (§C.3) | `agentcollab`, `agent`, `e` → disputed event |
| DELEGATE | 4504 | The block (§E) | `agentcollab`, `agent`, `p` → specialist pubkey |
| Charter | 34501 (replaceable, `d` = agent id) | The `agent_charter` block | `agentcollab` |
| Work claim | 4505 | Item id + status | `agentcollab`, `agent` |

Tag definitions:

- `["agentcollab", "<protocol ID>"]` — the full ID string from `bin/agentcollab-id.sh`, on **every** protocol event. This is the handshake made ambient: agreement is checked per event, not per session.
- `["agent", "<agent id>"]` — the charter id, cross-checkable against the author pubkey via the charter event.
- `["anchor", "<commit sha>"]` — the envelope's anchor commit; where the deployment uses NIP-34, also an `e` tag to the corresponding patch/repo event.
- Threading uses standard NIP-10 `e`/`p` tags, so INVENTORY and CONFLICT records appear as replies under the envelope they answer — the session's whole negotiation is one thread.

The markdown block remains the payload, unchanged from the core spec: a Buzz-bound agent and a file-bound agent produce byte-identical blocks, and the spec's "bare prose does not count" rule applies to event content exactly as it applies to session output.

## Relay-enforced handshake

The channel pins its protocol ID (in the channel topic or a pinned configuration event). A `buzz-workflow` automation watches protocol events and enforces the tag. Illustrative shape (the YAML schema is Buzz's; adjust to the deployed version):

```yaml
# illustrative — align with your buzz-workflow schema
name: agentcollab-handshake-gate
on:
  message:
    channels: [proj-yourproject]
    kinds: [4501, 4502, 4503, 4504, 4505]
steps:
  - when: missing_tag("agentcollab")
    do: reply("Protocol event without an AgentCollab ID tag. See the channel profile.")
  - when: tag("agentcollab") != pinned("agentcollab_id")
    do: reply("Protocol ID mismatch — run bin/agentcollab-verify.sh and resolve per Handshake §6 before continuing. No mutation under a disputed protocol.")
```

With this in place the version check moves up an enforcement tier: from *deployment-enforceable* (a session-start hook the operator remembers to install) to **infrastructure-enforced** (the relay's workflow engine flags every non-conforming event, for every participant, always). A stricter deployment can have the workflow escalate — remove the agent from the channel, open a work item — rather than merely reply.

## Control rebindings

- **D4 (records persist):** satisfied by relay persistence + `buzz-audit`. Envelope, inventory, and conflict events are signed and hash-chained; this exceeds the core's file-durability requirement.
- **D5 (concurrent-session detection):** rebound from polling to events. An agent publishes a work-claim event before mutating; the workflow (or the agent's own subscription) surfaces overlapping live claims immediately. Presence via the relay's pubsub answers "another *live* agent" directly, which file-based deployments can only approximate.
- **D6 (handshake before mutation):** unchanged for the agent (compute the ID by script, compare, stop on mismatch), *plus* the relay-side gate above as a second, independent check.

## What this binding does not change

The hashed bundle, the protocol ID, the precedence rule (ground truth > charter > handoff plan), the INVENTORY-first receiver obligation, and the honesty stance all stand unmodified. In particular: signed events prove **who published a claim**, and the handshake tag proves **which rules they committed to** — neither proves the claim is true or the rules were obeyed. The receiver still verifies claims against ground truth, and behavioral compliance remains instructed-only, now with a far better audit trail when it fails.

## Enforcement tiers under this binding

| Mechanism | Tier |
|---|---|
| Bundle integrity + maintainer signature (`agentcollab-verify.sh`) | shell-enforced |
| Sender identity (event signature + NIP-42 + charter pubkey match) | infrastructure-enforced |
| Protocol-ID agreement per event (workflow gate) | infrastructure-enforced |
| Record durability (relay + audit hash chain) | infrastructure-enforced |
| INVENTORY-before-edit, conflict logging, delegation discipline | instructed-only |

## Open questions for implementation

1. Kind numbers: adopt the provisional 45xx/345xx values or negotiate a range with the Buzz project.
2. Charter authority: who may publish or replace a charter event — operator key only, or agent self-registration gated by roster membership?
3. Mismatch escalation policy: reply, flag, or eject — per channel, declared in the profile.
4. Cross-community handoffs: two Buzz communities on different relays require the envelope event to be republished or referenced; specify which.
5. Whether the envelope's USER-HANDOFF block (human-facing) renders specially in Buzz clients or stays plain markdown.

## Adoption path

1. Publish this spec (done, if you are reading it in the repository).
2. Stand up the Buzz deployment; give each agent a keypair and a charter event.
3. Pin the protocol ID in the project channel; install the handshake-gate workflow.
4. Run the two-agent tutorial (`TUTORIAL.md`) with the session log rebound to the channel — the writer's envelope and the reviewer's inventory land as a signed thread.
5. Contribute the kind-number and workflow conventions upstream to the Buzz community as a proposed integration.
