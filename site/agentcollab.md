# AgentCollab — Signing Key & Release Verification

This page is the out-of-band trust anchor for [AgentCollab](https://github.com/CaptainMcCrank/AgentCollab), my cryptographically verifiable collaboration protocol for AI agents. The protocol's `Handshake.md` §7 explains why this page exists: the signing key travels inside the repository for convenience, so a wholesale fork could replace both the protocol text *and* the key. Pinning the key from this domain — which the repository does not control — is what makes an L2 verification mean "unmodified from upstream."

## Maintainer signing key

If the `keys/allowed_signers` file in your copy of the repository does not match this line byte-for-byte, do not trust that copy:

```
patrickmccanna@gmail.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGAXh8tgoxXeHynu1lkhpgBkoFtZa5dxy8HEyy52kGgs
```

Fingerprint, for at-a-glance comparison:

```
ED25519 SHA256:QzsA94AxteAb+u4NZXUuZltfXT6JOhdkALs3onZqF2U
```

This key signs `PROTOCOL_MANIFEST.yaml` (SSH signature, namespace `agentcollab-manifest`). It is stable across releases; this page changes only if the key is ever rotated.

## Verifying a copy against this page

```sh
# 1. Confirm the trust store matches the key above
cat keys/allowed_signers

# 2. Verify the bundle: file hashes ↔ signed manifest ↔ this key
./bin/agentcollab-verify.sh
# expect: acp-verify: RESULT: VERIFIED [L2] AgentCollab/<version>#sha256:<root16>
```

Or, without trusting the copy's own trust store, verify directly against this page: save the key line above as `signers`, then:

```sh
ssh-keygen -Y verify -f signers -I patrickmccanna@gmail.com \
  -n agentcollab-manifest -s PROTOCOL_MANIFEST.yaml.sig < PROTOCOL_MANIFEST.yaml
```

## Current release

**[v1.0.0](https://github.com/CaptainMcCrank/AgentCollab/releases/tag/v1.0.0)** — protocol ID:

```
AgentCollab/1.0.0#sha256:c031fa97e660faac
```

Full bundle root (the ID truncates it to 16 hex characters for display):

```
c031fa97e660faac83f19ba4edfaf1731b3b415d88de6d1e6a225d920197278f
```

Two agents that each independently compute this ID from their own local files (`bin/agentcollab-id.sh`) — and verify their manifests against the key above — are provably operating under the same, unmodified rules. What that does and doesn't guarantee is spelled out honestly in the spec: cryptography proves the *rules* are identical and authentic; nothing can prove a language model followed them.

For all releases and per-file hashes, see the [releases page](https://github.com/CaptainMcCrank/AgentCollab/releases) — each release attaches its `PROTOCOL_MANIFEST.yaml`, detached signature, and `allowed_signers` as standalone assets.
