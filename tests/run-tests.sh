#!/bin/sh
# Fixture tests for the AgentCollab handshake tooling.
# Proves the proof mechanism: a known-good bundle verifies, every tampered
# variant fails, and the signature layer accepts/rejects correctly.
# No LLM, no network. Ephemeral SSH key generated per run.
#
# Exit: 0 all pass · 1 any failure. Last line: RESULT pass=<n> fail=<n>

set -u

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

pass=0; fail=0
ok()  { pass=$((pass+1)); printf 'PASS %s\n' "$1"; }
ko()  { fail=$((fail+1)); printf 'FAIL %s\n' "$1"; }
check() { # check <name> <expected-exit> <actual-exit>
    [ "$2" -eq "$3" ] && ok "$1" || ko "$1 (expected exit $2, got $3)"
}

# --- Fixture: a copy of the real repo, re-signed with an ephemeral key -----
FIX="$WORK/fixture"
mkdir -p "$FIX"
cp -R "$REPO_DIR/protocol" "$REPO_DIR/bin" "$FIX/"
cp "$REPO_DIR/VERSION" "$FIX/"
mkdir -p "$FIX/keys"

ssh-keygen -q -t ed25519 -N '' -C 'acp-test' -f "$WORK/testkey" </dev/null
printf 'test@agentcollab ' > "$FIX/keys/allowed_signers"
cut -d' ' -f1-2 "$WORK/testkey.pub" >> "$FIX/keys/allowed_signers"

( cd "$FIX" && ./bin/agentcollab-id.sh --write >/dev/null 2>&1 )
( cd "$FIX" && ssh-keygen -Y sign -f "$WORK/testkey" -n agentcollab-manifest \
      PROTOCOL_MANIFEST.yaml >/dev/null 2>&1 )

clone() { rm -rf "$WORK/case"; cp -R "$FIX" "$WORK/case"; }

# --- 1. Known-good bundle: L1 and L2 verify; ID is stable ------------------
clone
( cd "$WORK/case" && ./bin/agentcollab-verify.sh --no-sig >/dev/null 2>&1 ); check "good bundle verifies at L1" 0 $?
( cd "$WORK/case" && ./bin/agentcollab-verify.sh >/dev/null 2>&1 );          check "good bundle verifies at L2" 0 $?
id1=$( cd "$WORK/case" && ./bin/agentcollab-id.sh )
id2=$( cd "$WORK/case" && ./bin/agentcollab-id.sh )
[ -n "$id1" ] && [ "$id1" = "$id2" ] && ok "protocol ID is deterministic ($id1)" \
    || ko "protocol ID not deterministic ('$id1' vs '$id2')"

# --- 2. Tampered document: one byte flipped in the spec --------------------
clone
printf ' ' >> "$WORK/case/protocol/Agent_Collaboration_Protocol.md"
( cd "$WORK/case" && ./bin/agentcollab-verify.sh --no-sig >/dev/null 2>&1 ); check "tampered doc fails L1" 1 $?
id3=$( cd "$WORK/case" && ./bin/agentcollab-id.sh )
[ "$id3" != "$id1" ] && ok "tampered doc changes the protocol ID" \
    || ko "tampered doc did NOT change the protocol ID"

# --- 3. Tampered manifest: forged hash without re-signing ------------------
clone
( cd "$WORK/case" && ./bin/agentcollab-id.sh --write >/dev/null 2>&1 )   # regen manifest, sig now stale
printf ' ' >> "$WORK/case/protocol/Agent_Charter.md"
( cd "$WORK/case" && ./bin/agentcollab-id.sh --write >/dev/null 2>&1 )   # manifest matches tampered files...
( cd "$WORK/case" && ./bin/agentcollab-verify.sh --no-sig >/dev/null 2>&1 ); check "regenerated manifest passes L1 (integrity only)" 0 $?
( cd "$WORK/case" && ./bin/agentcollab-verify.sh >/dev/null 2>&1 );          check "...but stale signature fails L2" 1 $?

# --- 4. Missing bundle file ------------------------------------------------
clone
rm "$WORK/case/protocol/Handshake.md"
( cd "$WORK/case" && ./bin/agentcollab-verify.sh --no-sig >/dev/null 2>&1 ); check "missing bundle file fails L1" 1 $?

# --- 5. Version/ID consistency: version edit without root change -----------
clone
sed -i 's/^version: .*/version: 9.9.9/' "$WORK/case/PROTOCOL_MANIFEST.yaml"
( cd "$WORK/case" && ./bin/agentcollab-verify.sh --no-sig >/dev/null 2>&1 ); check "version forged in manifest fails L1 (id/version/root disagree)" 1 $?

# --- 6. Wrong signing key --------------------------------------------------
clone
ssh-keygen -q -t ed25519 -N '' -C 'imposter' -f "$WORK/badkey" </dev/null
rm "$WORK/case/PROTOCOL_MANIFEST.yaml.sig"   # ssh-keygen -Y sign prompts rather than overwrite
( cd "$WORK/case" && ssh-keygen -Y sign -f "$WORK/badkey" -n agentcollab-manifest \
      PROTOCOL_MANIFEST.yaml >/dev/null 2>&1 )
( cd "$WORK/case" && ./bin/agentcollab-verify.sh >/dev/null 2>&1 );          check "signature from untrusted key fails L2" 1 $?

printf 'RESULT pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
