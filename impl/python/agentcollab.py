#!/usr/bin/env python3
"""agentcollab.py — Python reference implementation of the AgentCollab handshake.

Implements Handshake.md §2–§3 (bundle root, protocol ID) and §5 verification
(L1 integrity always; L2 authenticity via the system `ssh-keygen`, when
available). Standard library only. The shell scripts in bin/ remain the
normative reference; this module must produce byte-identical IDs — CI enforces
parity (tests/run-impl-parity.sh).

CLI (mirrors bin/agentcollab-id.sh and bin/agentcollab-verify.sh):
  agentcollab.py id      [--root DIR]            print the protocol ID
  agentcollab.py root    [--root DIR]            print the full 64-hex bundle root
  agentcollab.py verify  [--root DIR] [--no-sig] verify: exit 0 ok, 1 failed

Library:
  bundle_root(root_dir) -> str
  protocol_id(root_dir) -> str
  verify(root_dir, check_sig=True) -> (ok: bool, level: str, errors: list[str])

Exit codes: 0 ok · 1 verification failed · 2 usage/environment error
"""
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

NAMESPACE = "agentcollab-manifest"
MANIFEST = "PROTOCOL_MANIFEST.yaml"


class ManifestError(Exception):
    """Manifest missing, unreadable, or malformed."""


def _read_manifest(root_dir):
    path = Path(root_dir) / MANIFEST
    if not path.is_file():
        raise ManifestError(f"{MANIFEST} not found in {root_dir}")
    version, files, declared_root, declared_id = None, [], None, None
    current = None
    for line in path.read_text().splitlines():
        if m := re.match(r"^version: (\S+)$", line):
            version = m.group(1)
        elif m := re.match(r"^  - path: (\S+)$", line):
            current = m.group(1)
        elif m := re.match(r"^    sha256: ([0-9a-f]{64})$", line):
            if current is None:
                raise ManifestError("sha256 line without a preceding path")
            files.append((current, m.group(1)))
            current = None
        elif m := re.match(r"^bundle_root: ([0-9a-f]{64})$", line):
            declared_root = m.group(1)
        elif m := re.match(r"^id: (\S+)$", line):
            declared_id = m.group(1)
    if version is None or not files:
        raise ManifestError(f"{MANIFEST} is missing version or file entries")
    return {"version": version, "files": files,
            "bundle_root": declared_root, "id": declared_id}


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def bundle_root(root_dir):
    """Handshake §2: sha256 over the path-sorted '<hash>  <path>' listing."""
    root_dir = Path(root_dir)
    manifest = _read_manifest(root_dir)
    lines = []
    for rel, _ in manifest["files"]:
        target = root_dir / rel
        if not target.is_file():
            raise ManifestError(f"bundle file missing: {rel}")
        lines.append(f"{_file_sha256(target)}  {rel}")
    # Byte-wise path sort, matching `LC_ALL=C sort -k 2` on ASCII paths.
    lines.sort(key=lambda l: l.split("  ", 1)[1].encode())
    listing = "".join(line + "\n" for line in lines)
    return hashlib.sha256(listing.encode()).hexdigest()


def protocol_id(root_dir):
    manifest = _read_manifest(root_dir)
    return f"AgentCollab/{manifest['version']}#sha256:{bundle_root(root_dir)[:16]}"


def _verify_signature(root_dir, errors):
    root_dir = Path(root_dir)
    sig = root_dir / f"{MANIFEST}.sig"
    signers = root_dir / "keys" / "allowed_signers"
    if not sig.is_file():
        errors.append(f"signature {sig.name} not found (use check_sig=False for L1)")
        return
    if not signers.is_file():
        errors.append("trust store keys/allowed_signers not found")
        return
    if shutil.which("ssh-keygen") is None:
        errors.append("ssh-keygen not available: L2 cannot be checked on this host "
                      "(rerun with --no-sig for L1, or verify on a host with OpenSSH >= 8.1)")
        return
    # During key rotation allowed_signers lists several principals; the
    # signature is valid if it verifies for any of them.
    principals = list(dict.fromkeys(
        line.split()[0] for line in signers.read_text().splitlines()
        if line.strip() and not line.startswith("#")))
    if not principals:
        errors.append("no principal found in keys/allowed_signers")
        return
    for principal in principals:
        result = subprocess.run(
            ["ssh-keygen", "-Y", "verify", "-f", str(signers), "-I", principal,
             "-n", NAMESPACE, "-s", str(sig)],
            stdin=open(root_dir / MANIFEST, "rb"),
            capture_output=True)
        if result.returncode == 0:
            return
    errors.append("manifest signature INVALID for every listed principal")


def verify(root_dir, check_sig=True):
    """Handshake §5. Returns (ok, level, errors); level is 'L1' or 'L2'."""
    root_dir = Path(root_dir)
    errors = []
    manifest = _read_manifest(root_dir)
    for rel, declared in manifest["files"]:
        target = root_dir / rel
        if not target.is_file():
            errors.append(f"MISSING {rel}")
        elif _file_sha256(target) != declared:
            errors.append(f"MISMATCH {rel}")
    if not errors:
        computed = bundle_root(root_dir)
        if computed != manifest["bundle_root"]:
            errors.append(f"bundle root mismatch: computed {computed}, "
                          f"manifest declares {manifest['bundle_root']}")
        expected_id = f"AgentCollab/{manifest['version']}#sha256:{computed[:16]}"
        if expected_id != manifest["id"]:
            errors.append(f"id/version/root disagree: manifest id '{manifest['id']}', "
                          f"derived '{expected_id}'")
    level = "L2" if check_sig else "L1"
    if check_sig:
        _verify_signature(root_dir, errors)
    return (not errors, level, errors)


def _main(argv):
    if not argv or argv[0] not in ("id", "root", "verify"):
        sys.stderr.write(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    root_dir = "."
    check_sig = True
    while rest:
        arg = rest.pop(0)
        if arg == "--root":
            if not rest:
                sys.stderr.write("agentcollab: --root needs a value\n")
                return 2
            root_dir = rest.pop(0)
        elif arg == "--no-sig":
            check_sig = False
        else:
            sys.stderr.write(f"agentcollab: unknown option {arg}\n")
            return 2
    try:
        if cmd == "id":
            print(protocol_id(root_dir))
        elif cmd == "root":
            print(bundle_root(root_dir))
        else:
            ok, level, errors = verify(root_dir, check_sig=check_sig)
            for err in errors:
                print(f"agentcollab: FAIL: {err}", file=sys.stderr)
            if not ok:
                print(f"agentcollab: RESULT: FAILED ({level})")
                return 1
            print(f"agentcollab: RESULT: VERIFIED [{level}] {protocol_id(root_dir)}")
    except ManifestError as exc:
        sys.stderr.write(f"agentcollab: {exc}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
