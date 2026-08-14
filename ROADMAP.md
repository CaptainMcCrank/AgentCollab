# Roadmap

Follow-on work, ordered by leverage. Items marked **bundle** touch files under `protocol/` and therefore change the protocol ID (version bump + re-sign per `Handshake.md` §9); everything else ships without a release.

## 1. JSON Schemas for protocol blocks — SHIPPED (tooling tier)

Shipped: `schemas/` (all six blocks), `bin/acp-lint.py` (stdlib-only parser + validator; PyYAML for charters), valid/invalid fixtures under `tests/fixtures/`, and a CI job. Remaining for v1.1.0: reference the schemas from the spec to make them normative.

**Goal:** make every labeled block machine-checkable, so harnesses and frameworks can validate protocol activity instead of trusting prose.
**Deliverables:** `schemas/` directory with JSON Schema for CONTEXT-HANDOFF, INVENTORY, CONFLICT, DELEGATE, USER-HANDOFF, and the `agent_charter` block; a `bin/acp-lint.sh` (or Python equivalent) that validates a markdown block against its schema; CI job running the linter over the spec's own examples.
**Steps:** extract field lists from spec §A–§E → author schemas (blocks stay markdown; schemas define the parsed field structure) → add example fixtures (valid + invalid) → wire into CI.
**Version impact:** none until the spec *references* the schemas as normative; do that referencing in the next bundle release. **Effort:** one to two sessions. **This unblocks items 2, 4, and 6.**

## 2. Conformance suite — SHIPPED (v1, six scenarios)

Shipped: `conformance/` with six scenarios (S01 clean handoff, S02 stale claim, S03 ID mismatch, S04 missing fields, S05 out-of-scope work, S06 concurrent claim), the `run.py` prepare/grade runner with a deterministic LLM-free grader, reference transcripts, a scoring rubric (`conformance/README.md`), and a CI self-test proving the grader accepts the references and rejects broken runs. Open: more scenarios (rules 2, 6–9, 11–12 lack dedicated coverage) and a periodically refreshed reference-subject result.

**Goal:** let an implementation claim "passes AgentCollab conformance vN" — behavioral proof, complementing the handshake's byte-level proof, and the honest answer to "identical text does not guarantee identical interpretation."
**Deliverables:** `conformance/` with scripted scenarios (stale-claim envelope → expect divergent INVENTORY; missing envelope fields → expect request/reconstruct; protocol ID mismatch → expect CONFLICT and no mutation; out-of-scope work → expect DELEGATE); a runner that presents each scenario to an agent-under-test and grades the labeled blocks it emits (using item 1's schemas); a published scoring rubric.
**Steps:** enumerate testable rules from the README's fifteen → author fixtures per rule → build the grader → run against Claude Code as the reference subject → document pass criteria.
**Version impact:** none. **Effort:** the largest item; several sessions. Depends on item 1.

## 3. Python and JavaScript reference implementations — SHIPPED (cores)

Shipped: `impl/python/agentcollab.py` (Python ≥ 3.8, stdlib only) and `impl/js/agentcollab.mjs` (Node ≥ 18, stdlib only) — bundle root, protocol ID, L1 verification natively, L2 via the system `ssh-keygen` with a documented fail-closed fallback. `tests/run-impl-parity.sh` (12 checks, in CI) enforces byte-identical parity with the shell scripts on good and tampered trees. Open: PyPI/npm packaging after v1.1.0.

**Goal:** remove the POSIX-shell dependency that excludes browser-based, API-wrapped, and Windows agents from computing the protocol ID at all.
**Deliverables:** `impl/python/agentcollab.py` and `impl/js/agentcollab.mjs`, each implementing the Handshake §2 algorithm (bundle root + ID) and §5 verification (L1; L2 where an SSH-signature library exists — document the fallback where it does not); cross-checked in CI against `bin/acp-id.sh` output on the same tree.
**Steps:** port the hashing algorithm → port manifest parsing → CI parity job (all three implementations must emit the identical ID) → publish to PyPI/npm once stable.
**Version impact:** none; the shell scripts remain the reference. **Effort:** one session for both cores; packaging adds another.

## 4. Agent-native distribution

**Goal:** agents do not browse GitHub; put the protocol where agents and frameworks actually load capabilities.
**Deliverables:** a Claude Code skill/plugin that teaches the protocol and wraps the scripts; an MCP server exposing `agentcollab_id` and `agentcollab_verify` tools (item 3's Python core); `llms.txt` on the trust-anchor page; an AGENTS.md snippet template for consuming projects.
**Steps:** skill first (fastest, this ecosystem) → MCP server → llms.txt → announce.
**Version impact:** none. **Effort:** skill in one session; MCP server one more. Depends on item 3 for the MCP path.

## 5. Governance, key rotation, and fork guidance

**Goal:** answer the questions a serious adopter asks about a one-person protocol before depending on it.
**Deliverables:** `GOVERNANCE.md` covering: how spec changes are proposed and accepted; the key-rotation and revocation procedure (and what happens to old releases' verifiability); the bus-factor plan (second anchor, successor key policy); explicit fork guidance (forks change the ID automatically — forkers must also change the `AgentCollab` prefix); a statement scoping "higher signed version wins" to same-maintainer bundles.
**Steps:** draft → publish → reference from README and the trust-anchor page.
**Version impact:** the fork-prefix rule belongs in `Handshake.md` eventually — **bundle**, fold into the next release alongside item 1's schema references. **Effort:** one session.

## 6. Buzz adapter (transport + identity binding)

**Goal:** bind the protocol to [block/buzz](https://github.com/block/buzz) so envelopes become signed relay events, agent identity becomes keypair-backed (NIP-42), and the handshake becomes relay-enforced via a workflow that checks a protocol-ID tag on every event.
**Deliverables:** `adapters/buzz.md` design spec (see it for detail); later, once a Buzz deployment is running: the workflow implementation and a worked demo.
**Version impact:** none — adapters are outside the bundle. **Effort:** spec now; implementation gated on a running Buzz instance.

## 7. Script naming (deferred)

`bin/acp-id.sh` / `bin/acp-verify.sh` collide with Buzz's "ACP" (Agent Communication Protocol, the agent-harness protocol). The protocol ID string already says `AgentCollab` and is unaffected. Plan: introduce `agentcollab-*` script names with `acp-*` kept as compatibility aliases, in the same bundle release as items 1 and 5 (the spec references script names, so the rename is a bundle edit). Until then, integration docs spell out "AgentCollab" and avoid the acronym.

## Sequencing

Schemas (1) → conformance (2) and MCP/skill (4) in parallel with reference implementations (3); governance (5) drafted alongside; one consolidated bundle release (v1.1.0) picks up the schema references, the fork-prefix rule, the script rename, and a wording fix to the spec's INVENTORY template (its `<protocol ID … — L0/L1/L2 …>` placeholder invites free-text annotation; the canonical form is `<ID> [Lx]`, annotation after a dash — found by the live S02 reference run) — one re-sign, one ID change, instead of three. The Buzz adapter (6) ships independently, starting now.
