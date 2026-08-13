# Handshake: Cryptographic Protocol Agreement

**Purpose:** Define how two agents establish — cheaply, and with cryptographic backing — that they are operating under the same, unmodified version of the Agent Collaboration Protocol.

**The design in one line:** agreement by exchange of a compact, independently recomputed identifier (the *protocol ID*), backed by a hash manifest and a maintainer signature — the same pattern TLS uses for cipher-suite agreement and package managers use for lock files.

---

## 1. Definitions

| Term | Definition |
|---|---|
| **bundle** | The set of normative protocol documents, enumerated in the manifest. In this release: everything under `protocol/`. |
| **manifest** | `PROTOCOL_MANIFEST.yaml` at the repository root: the bundle file list with per-file SHA-256 hashes, the bundle root, the version, and the protocol ID. |
| **bundle root** | A single SHA-256 that commits to every byte of every bundle file (§2). |
| **protocol ID** | The compact string agents exchange: `AgentCollab/<version>#sha256:<first 16 hex of bundle root>`. |
| **maintainer signature** | A detached SSH signature (`PROTOCOL_MANIFEST.yaml.sig`) over the manifest, verifiable against `keys/allowed_signers`. |

## 2. Computing the bundle root (normative)

1. For each `path` listed in the manifest's `files:` section, compute the SHA-256 of the file's **raw bytes** (no newline normalization, no encoding transformation — the bytes as committed).
2. Produce one line per file, in the `sha256sum` output format — the 64-hex-digit lowercase hash, two spaces, the path exactly as listed in the manifest:

   ```
   <sha256>  <path>
   ```

3. Sort the lines by path, byte-wise ascending (`LC_ALL=C sort -k 2`).
4. The **bundle root** is the SHA-256 of the sorted listing, newline-terminated (every line, including the last, ends with `\n`).

Equivalent shell, from the repository root:

```sh
LC_ALL=C sha256sum <paths-from-manifest, sorted> | sha256sum
```

`bin/acp-id.sh` implements this and prints the protocol ID; it is the reference implementation. **Agents must obtain the protocol ID by running it — never by computing hashes "mentally," recalling them from context, or echoing a counterparty's value.** A language model cannot compute SHA-256; any protocol ID not produced by a tool invocation is fabricated by definition.

## 3. The protocol ID

```
AgentCollab/<semver>#sha256:<first 16 hex chars of bundle root>
```

Example: `AgentCollab/1.0.0#sha256:3f9a2c1e8b44d071`.

- The 16-hex (64-bit) prefix keeps the ID compact in session output; the full root lives in the manifest and is what `acp-verify.sh` checks. The truncation is a display convention, not the security boundary — any dispute escalates to full-root and signature comparison (§6).
- The version and the hash **travel together and must agree**: a bundle whose recomputed root does not match its manifest's claimed version fails verification regardless of what either string says.

## 4. The exchange

| Step | Actor | Action |
|---|---|---|
| 1 | Sender | Runs `bin/acp-id.sh`; writes the ID into the `Protocol:` field of the CONTEXT-HANDOFF envelope (and every labeled block it emits). |
| 2 | Receiver | **Independently** runs `bin/acp-id.sh` against its own local bundle, before any mutation (Collaboration Protocol §B.0). |
| 3 | Receiver | Compares the two strings. Equal → agreement established; the recomputed ID goes in the INVENTORY block. Unequal or absent → CONFLICT (§6); no mutation until resolved. |

The comparison is string equality: one line of context per party, deterministic, fail-fast. Note what step 2 rules out: a receiver that merely echoes the sender's ID has proven nothing. The value of the handshake is that both IDs are *derived from local bytes by a tool*, so equality is evidence about the files, not about the conversation.

## 5. Verification levels

| Level | Claim established | Mechanism | Cost |
|---|---|---|---|
| **L0 — agreement** | Both agents' bundles are byte-identical | Exchange + independent recomputation of the protocol ID (§4) | 2 script runs, string compare |
| **L1 — integrity** | The local bundle matches its own manifest exactly | `bin/acp-verify.sh --no-sig`: per-file hashes, bundle root, and manifest-internal consistency (root ↔ ID ↔ version) | 1 script run |
| **L2 — authenticity** | The bundle is the unmodified text the maintainer signed | `bin/acp-verify.sh`: L1 plus SSH signature verification of the manifest against `keys/allowed_signers` | 1 script run |

L0 alone protects against *drift between the two parties*. L2 protects against *both parties sharing the same tampered copy*, and is what lets two agents in different organizations, on different machines, trust the match: each verifies independently against the maintainer's published key, without trusting the other's filesystem.

**Deployments should run L2 at session start** (a session-start hook makes this shell-enforced rather than instructed-only) and record the level actually achieved in the INVENTORY block, e.g. `AgentCollab/1.0.0#sha256:3f9a2c1e8b44d071 [L2]`.

## 6. Mismatch (normative — referenced by Collaboration Protocol §C.5)

A protocol ID mismatch, or a missing `Protocol:` field, is a CONFLICT resolved in this order:

1. **Both parties run `bin/acp-verify.sh`** on their own bundles and report the result in the CONFLICT record.
2. **Verification failure loses.** A party whose bundle fails L1/L2 defers to a party whose bundle verifies. (Its next action is to restore a verified bundle — from the signed release, not from the counterparty's prose.)
3. **Both verify, different versions:** the higher version with a valid maintainer signature governs, provided the lower-version party can obtain and L2-verify that bundle. A version it cannot obtain and verify is `[unverifiable]` and cannot win.
4. **Anything else** — both verify at the same version but different roots (a manifest fork), signature disputes, unobtainable bundles — is `DEFER-TO-OPERATOR` with both verification transcripts attached.
5. **No mutation happens under a disputed protocol.**

## 7. Signing and key distribution

Signatures use OpenSSH signing (`ssh-keygen -Y`) — chosen over GPG because the tooling ships with every OpenSSH installation and the trust store is one file.

- `keys/allowed_signers` holds the maintainer principal and public key, one line: `<principal> <key-type> <base64-key>`.
- The signature namespace is `agentcollab-manifest`.
- Sign: `ssh-keygen -Y sign -f <private-key> -n agentcollab-manifest PROTOCOL_MANIFEST.yaml`
- Verify (what `acp-verify.sh` runs): `ssh-keygen -Y verify -f keys/allowed_signers -I <principal> -n agentcollab-manifest -s PROTOCOL_MANIFEST.yaml.sig < PROTOCOL_MANIFEST.yaml`

**Trust bootstrap:** the `allowed_signers` file travels inside the repository for convenience, which means a wholesale fork could replace both text and key. Importers who need L2 to mean "unmodified from *upstream*" should pin the maintainer key from an out-of-band source (the project's release page, the maintainer's site) or pin the signed git tag of the release they imported. This is the standard lock-file trust model; the handshake does not pretend otherwise.

For this distribution, the maintainer key's out-of-band anchor is **<https://patrickmccanna.net/agentcollab>** — it serves the key fingerprint, a machine-readable `allowed_signers` copy, and verification instructions from a domain the repository does not control.

## 8. What this proves — and what it cannot

**Proves:** both agents hold byte-identical protocol text (L0); that text is internally consistent with its manifest (L1); that text is what the maintainer signed (L2). Integrity and authenticity of the *rules*.

**Cannot prove:** that either language model *followed* the rules. Behavioral compliance remains instructed-only (see Collaboration Protocol §Enforcement honesty), narrowed by deployment hooks. The handshake eliminates the failure class where agents diverge because they held different rules, and makes rule-set divergence a detectable, loggable event instead of a silent one.

## 9. Releasing (change control)

Any byte change to any bundle file is a new release. Procedure:

1. Edit the bundle files.
2. Bump `version:` (semver: breaking block-format or precedence changes = major; additive = minor; editorial = patch) in `VERSION` and the manifest.
3. Regenerate the manifest: `bin/acp-id.sh --write` recomputes every file hash, the bundle root, and the ID (taking the version from `VERSION`), and rewrites `PROTOCOL_MANIFEST.yaml`.
4. Re-sign: `ssh-keygen -Y sign -f <key> -n agentcollab-manifest PROTOCOL_MANIFEST.yaml`
5. Commit; tag `v<version>` (a signed git tag, `git tag -s`, is recommended — it gives importers a second, independent authenticity anchor).

A manifest whose hashes don't match the files, or whose signature is stale, fails `acp-verify.sh` — there is no way to ship a silent revision that verifies.
