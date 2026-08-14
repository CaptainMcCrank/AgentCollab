# Governance

The questions a serious adopter asks about a one-person protocol, answered before they have to ask. Like everything else here, this document is honest about its enforcement tier: the cryptography is enforced; the procedures below are commitments.

## Maintainership

AgentCollab has a single maintainer: **Patrick McCanna** (`patrickmccanna@gmail.com`, [@CaptainMcCrank](https://github.com/CaptainMcCrank)). The maintainer decides what merges and what releases. There is no committee and no voting — with one structural check: **no silent revisions are possible**. Every normative change alters the bundle root and therefore the protocol ID, requires a re-signed manifest, and is visible to every verifier. The maintainer can change the rules; the maintainer cannot change them quietly.

## How the spec changes

1. **Propose** via a GitHub issue or pull request. Anything is proposable; changes to `protocol/` get the most scrutiny because they change the ID every deployment pins.
2. **Accept** — the maintainer merges. Normative changes (anything under `protocol/`) batch toward a release rather than landing one-by-one, so consumers see few ID changes, each well-described.
3. **Release** per `Handshake.md` §9: bump `VERSION`, regenerate the manifest, re-sign, tag, publish with the new protocol ID in the release notes.

**Semver meaning for the bundle:** **major** — block formats, precedence rules, or controls change incompatibly (a conforming v1 agent would misbehave under v2); **minor** — additive (new optional fields, new sections, new controls that don't invalidate old behavior); **patch** — editorial (wording, examples, typos). Files outside `protocol/` (tooling, schemas, conformance, distribution, this document) change without a release and never affect the ID.

## Keys

**Current maintainer key:** ssh-ed25519, principal `patrickmccanna@gmail.com`, fingerprint:

```
SHA256:QzsA94AxteAb+u4NZXUuZltfXT6JOhdkALs3onZqF2U
```

Published in `keys/allowed_signers` (in-repo convenience copy), attached to every GitHub release, and anchored out-of-band at [patrickmccanna.net/agentcollab](https://patrickmccanna.net/agentcollab) — the anchor page is the authority when the copies disagree, because it lives on a domain the repository cannot alter. SSH keys do not expire; the key changes only by the procedures below.

### Rotation (planned key change)

1. Generate the new key; add its line to `keys/allowed_signers` **alongside** the old one (the file supports multiple entries; `acp-verify.sh` accepts a signature from any listed principal — pass `--signer` to pin one).
2. Update the trust-anchor page: new key added, old key moved to a dated "previous keys" section.
3. Sign the next release with the new key. Both keys remain listed for a transition window of at least one release cycle, so mid-upgrade consumers verify either.
4. After the window, remove the old key from `allowed_signers` in a subsequent release. Historical releases stay verifiable forever: each release's attached `allowed_signers` names the key that signed *it*, and the anchor page's key history confirms that key was legitimate for that period.

### Revocation (compromise)

If the signing key is compromised, the repository itself must be presumed attacker-writable (the key signs what the repo distributes), so recovery runs through the out-of-band anchor:

1. **The anchor page is updated first**: compromise notice, the compromised fingerprint marked revoked with the discovery date, the new key, and the last release tag known good (created before the compromise window).
2. A new release is cut, signed only by the new key, with `allowed_signers` listing only the new key.
3. Consumers re-pin from the anchor page and re-verify their vendored copies; anything verifying only against the revoked key is treated as untrusted until re-verified.

**Honest limit:** SSH signatures carry no trusted timestamp, so an attacker holding the old key can forge signatures that *look* pre-compromise. After a revocation, "signed by the old key" proves nothing by itself — trust flows from the anchor page's last-known-good statement and from independent timestamps (the GitHub release history, consumers' own vendored copies and lock files), not from old signatures.

## Continuity (the bus factor)

Stated plainly: one maintainer, one key, one anchor domain. Mitigations, in order of what an adopter can rely on today:

- **The license is the ultimate continuity plan.** Apache-2.0 means anyone can fork and continue, at any time, for any reason — see fork guidance below.
- **Vendored copies don't rot.** A deployment that pinned a verified release keeps working and verifying forever; nothing in the protocol phones home.
- **Abandonment policy:** if the maintainer is unresponsive to issues and security reports for **six months**, treat the protocol as unmaintained. Serious continuations should fork under a new name per the guidance below rather than waiting; a fork by an established consumer, announcing its own anchor, is the intended succession mechanism.
- A second signer and a second anchor domain are desirable future hardening; neither exists today, and this document will say so until they do.

## Forks

Forking is legitimate and Apache-2.0 makes it legal. The rules keep a mixed ecosystem coherent:

1. **The hash does the first half automatically** — any edit to the bundle changes the bundle root, so a fork can never impersonate an upstream release byte-for-byte.
2. **Forks MUST change the name prefix.** A modified bundle must not identify as `AgentCollab/...`: change the `protocol:` field in the manifest and the ID prefix (e.g. `YourCollab/1.0.0#sha256:...`) so mismatch handling in mixed deployments never confuses lineage with identity. (This rule becomes normative in `Handshake.md` in v1.1.0; it is stated here first.)
3. **Forks MUST ship their own key and anchor.** Replace `keys/allowed_signers`, sign with your own key, publish your own out-of-band anchor. Never point at patrickmccanna.net.
4. **Stating lineage is encouraged:** "derived from `AgentCollab/1.0.1#sha256:ecce17042a867fe9`" in the fork's README gives consumers the audit trail without the identity claim.

## Scope of "higher signed version wins"

`Handshake.md` §6 resolves a version mismatch in favor of the higher version *with a valid maintainer signature*. Precisely scoped: **that rule applies only between bundles verifiable against the same trust store the verifier has pinned.** A higher-version bundle signed by any other key — including a fork, and including a "newer AgentCollab" a counterparty offers during a dispute — is `[unverifiable]` under §C.1's information-parity rule and cannot win; the mismatch escalates to `DEFER-TO-OPERATOR`. Version precedence is a tiebreaker within one maintainer's lineage, never a mechanism for a stranger's bundle to displace yours.

## Security reports

Report vulnerabilities in the protocol design or the tooling to `patrickmccanna@gmail.com` rather than a public issue. The maintainer's target is acknowledgment within a week; the abandonment policy above is the fallback if that stops being true.
