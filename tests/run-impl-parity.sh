#!/bin/sh
# Reference-implementation parity: the Python and JavaScript implementations
# must agree byte-for-byte with the normative shell scripts — same protocol
# ID, same bundle root, same verify verdicts on both a good and a tampered
# tree. JS checks are skipped (with a note) when node is absent.
# Exit: 0 all pass · 1 any failure. Last line: RESULT pass=<n> fail=<n> skip=<n>

set -u
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
pass=0; fail=0; skip=0

ok() { pass=$((pass+1)); printf 'PASS %s\n' "$1"; }
ko() { fail=$((fail+1)); printf 'FAIL %s\n' "$1"; }
eq() { [ "$2" = "$3" ] && ok "$1" || ko "$1 ('$2' vs '$3')"; }

HAVE_NODE=1
command -v node >/dev/null 2>&1 || { HAVE_NODE=0; skip=1; echo "SKIP node not found — JS parity not checked"; }

W=$(mktemp -d); trap 'rm -rf "$W"' EXIT

# --- parity on the real tree -------------------------------------------------
cd "$REPO"
sh_id=$(./bin/agentcollab-id.sh);  sh_root=$(./bin/agentcollab-id.sh --root)
py_id=$(python3 impl/python/agentcollab.py id); py_root=$(python3 impl/python/agentcollab.py root)
eq "python ID matches shell" "$sh_id" "$py_id"
eq "python root matches shell" "$sh_root" "$py_root"
python3 impl/python/agentcollab.py verify >/dev/null 2>&1 && ok "python verifies repo at L2" || ko "python L2 verify failed"
if [ "$HAVE_NODE" -eq 1 ]; then
    js_id=$(node impl/js/agentcollab.mjs id); js_root=$(node impl/js/agentcollab.mjs root)
    eq "js ID matches shell" "$sh_id" "$js_id"
    eq "js root matches shell" "$sh_root" "$js_root"
    node impl/js/agentcollab.mjs verify >/dev/null 2>&1 && ok "js verifies repo at L2" || ko "js L2 verify failed"
fi

# --- parity on a tampered tree: everyone must fail, identically --------------
cp -R "$REPO/protocol" "$REPO/bin" "$REPO/keys" "$W/"
cp "$REPO/PROTOCOL_MANIFEST.yaml" "$REPO/PROTOCOL_MANIFEST.yaml.sig" "$REPO/VERSION" "$W/"
printf ' ' >> "$W/protocol/Handshake.md"

( cd "$W" && ./bin/agentcollab-verify.sh >/dev/null 2>&1 ); sh_rc=$?
python3 "$REPO/impl/python/agentcollab.py" verify --root "$W" >/dev/null 2>&1; py_rc=$?
eq "shell fails tampered tree with exit 1" "1" "$sh_rc"
eq "python fails tampered tree with exit 1" "1" "$py_rc"
t_sh=$( cd "$W" && ./bin/agentcollab-id.sh )
t_py=$(python3 "$REPO/impl/python/agentcollab.py" id --root "$W")
eq "python tampered ID matches shell" "$t_sh" "$t_py"
[ "$t_py" != "$sh_id" ] && ok "tampering changes the ID" || ko "tampered ID unchanged"
if [ "$HAVE_NODE" -eq 1 ]; then
    node "$REPO/impl/js/agentcollab.mjs" verify --root "$W" >/dev/null 2>&1; js_rc=$?
    eq "js fails tampered tree with exit 1" "1" "$js_rc"
    eq "js tampered ID matches shell" "$t_sh" "$(node "$REPO/impl/js/agentcollab.mjs" id --root "$W")"
fi

# --- key rotation: two-key trust store, signature from the SECOND key --------
R="$W/rot"; mkdir -p "$R/keys"
cp -R "$REPO/protocol" "$R/protocol"
cp "$REPO/PROTOCOL_MANIFEST.yaml" "$REPO/VERSION" "$R/"
ssh-keygen -q -t ed25519 -N '' -C decoy -f "$W/decoykey" </dev/null
ssh-keygen -q -t ed25519 -N '' -C rot -f "$W/rotkey" </dev/null
{
    printf 'decoy@example ';  cut -d' ' -f1-2 "$W/decoykey.pub"
    printf 'rotated@example '; cut -d' ' -f1-2 "$W/rotkey.pub"
} > "$R/keys/allowed_signers"
( cd "$R" && ssh-keygen -Y sign -f "$W/rotkey" -n agentcollab-manifest \
      PROTOCOL_MANIFEST.yaml >/dev/null 2>&1 )
mkdir -p "$R/bin" && cp "$REPO/bin/agentcollab-verify.sh" "$REPO/bin/agentcollab-id.sh" "$R/bin/" && chmod +x "$R/bin/"*.sh

( cd "$R" && ./bin/agentcollab-verify.sh >/dev/null 2>&1 ) && ok "shell verifies with second-listed key (rotation)" || ko "shell rotation verify failed"
python3 "$REPO/impl/python/agentcollab.py" verify --root "$R" >/dev/null 2>&1 && ok "python verifies with second-listed key (rotation)" || ko "python rotation verify failed"
if [ "$HAVE_NODE" -eq 1 ]; then
    node "$REPO/impl/js/agentcollab.mjs" verify --root "$R" >/dev/null 2>&1 && ok "js verifies with second-listed key (rotation)" || ko "js rotation verify failed"
fi

printf 'RESULT pass=%d fail=%d skip=%d\n' "$pass" "$fail" "$skip"
[ "$fail" -eq 0 ]
