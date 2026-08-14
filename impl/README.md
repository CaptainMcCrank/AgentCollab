# Reference implementations

The POSIX shell scripts in `bin/` are the **normative** implementation of the handshake. These ports exist so agents without a shell — browser-based, API-wrapped, Windows-without-WSL — can compute and verify protocol IDs natively. Both are standard-library only and must produce byte-identical output to the shell scripts; CI enforces parity on every push (`tests/run-impl-parity.sh`: same ID, same bundle root, same verdicts on good and tampered trees).

| Implementation | Requires | Import | CLI |
|---|---|---|---|
| `python/agentcollab.py` | Python ≥ 3.8, stdlib only | `bundle_root(dir)`, `protocol_id(dir)`, `verify(dir, check_sig=True)` | `agentcollab.py id\|root\|verify [--root DIR] [--no-sig]` |
| `js/agentcollab.mjs` | Node ≥ 18, stdlib only | `bundleRoot(dir)`, `protocolId(dir)`, `verify(dir, {checkSig})` | `agentcollab.mjs id\|root\|verify [--root DIR] [--no-sig]` |

Exit codes match the shell scripts: 0 verified, 1 verification failed, 2 usage or environment error.

## The L2 caveat

L1 (integrity: files ↔ signed manifest ↔ declared ID) is implemented natively in both ports. L2 (authenticity: the manifest signature against `keys/allowed_signers`) shells out to the system `ssh-keygen`, because no SSH-signature verifier exists in either standard library. On a host without OpenSSH ≥ 8.1, `verify` reports that L2 cannot be checked and fails closed — run with `--no-sig` to accept L1 explicitly. A host that can reach neither `ssh-keygen` nor a vetted SSH-signature library should treat its copy as L1-verified at best and pin the release tag instead (`Handshake.md` §7).

## Parity discipline

Any behavioral change lands in the shell scripts first, then here, in the same commit, with `tests/run-impl-parity.sh` green. If the ports and the scripts ever disagree, the scripts are right and the port has a bug.

Packaging (PyPI / npm) is planned once the v1.1.0 bundle release settles — see `ROADMAP.md` item 3.
