#!/bin/sh
# agentcollab-verify.sh — verify the AgentCollab bundle: files ↔ manifest ↔ signature.
#
# Reference implementation of Handshake.md §5 (levels L1/L2).
#   L1: every bundle file matches its manifest hash; the recomputed bundle
#       root matches the manifest's bundle_root; root ↔ id ↔ version agree.
#   L2: L1 + the manifest carries a valid maintainer signature
#       (PROTOCOL_MANIFEST.yaml.sig against keys/allowed_signers).
#
# Usage:
#   agentcollab-verify.sh                 full L2 verification
#   agentcollab-verify.sh --no-sig        L1 only (integrity, no authenticity)
#   agentcollab-verify.sh --signer <id>   verify against a specific principal
#                                 (default: first principal in allowed_signers)
#
# Exit codes: 0 verified · 1 verification FAILED · 2 usage/environment error

set -u

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"
MANIFEST="PROTOCOL_MANIFEST.yaml"
SIG="$MANIFEST.sig"
SIGNERS="keys/allowed_signers"
NAMESPACE="agentcollab-manifest"

CHECK_SIG=1
SIGNER=""
while [ $# -gt 0 ]; do
    case "$1" in
        --no-sig) CHECK_SIG=0 ;;
        --signer) shift; SIGNER=${1:?--signer needs a value} ;;
        *) printf 'acp-verify: unknown option: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done

fail=0
say()  { printf 'acp-verify: %s\n' "$*"; }
bad()  { printf 'acp-verify: FAIL: %s\n' "$*" >&2; fail=1; }

command -v sha256sum >/dev/null 2>&1 || { say "sha256sum not found"; exit 2; }
[ -f "$MANIFEST" ] || { bad "$MANIFEST not found"; exit 1; }

# --- L1: per-file hashes ---------------------------------------------------
listing=$(awk '
    /^  - path: /   { path=$3 }
    /^    sha256: / { print $2 "  " path }
' "$MANIFEST")
[ -n "$listing" ] || { bad "no files listed in $MANIFEST"; exit 1; }

printf '%s\n' "$listing" | while IFS= read -r line; do
    p=${line#*  }
    [ -f "$p" ] || { printf 'MISSING %s\n' "$p"; continue; }
    printf '%s\n' "$line" | sha256sum -c --quiet - 2>/dev/null \
        || printf 'MISMATCH %s\n' "$p"
done | {
    n=0
    while IFS= read -r badline; do n=$((n+1)); printf 'acp-verify: FAIL: %s\n' "$badline" >&2; done
    exit "$n"
} || fail=1

# --- L1: bundle root and ID consistency ------------------------------------
declared_root=$(awk '/^bundle_root: /{print $2; exit}' "$MANIFEST")
declared_id=$(awk '/^id: /{print $2; exit}' "$MANIFEST")
declared_version=$(awk '/^version: /{print $2; exit}' "$MANIFEST")

computed_root=$(awk '/^  - path: /{print $3}' "$MANIFEST" \
    | while IFS= read -r p; do [ -f "$p" ] && sha256sum "$p"; done \
    | LC_ALL=C sort -k 2 | sha256sum | cut -c1-64)

[ "$computed_root" = "$declared_root" ] \
    || bad "bundle root mismatch: computed $computed_root, manifest declares $declared_root"

expected_id="AgentCollab/${declared_version}#sha256:$(printf '%s' "$computed_root" | cut -c1-16)"
[ "$expected_id" = "$declared_id" ] \
    || bad "id/version/root disagree: manifest id '$declared_id', derived '$expected_id'"

# --- L2: maintainer signature ----------------------------------------------
level="L1"
if [ "$CHECK_SIG" -eq 1 ]; then
    level="L2"
    if [ ! -f "$SIG" ]; then
        bad "signature $SIG not found (run with --no-sig for integrity-only L1)"
    elif [ ! -f "$SIGNERS" ]; then
        bad "trust store $SIGNERS not found"
    else
        # During key rotation allowed_signers lists several principals; the
        # signature is valid if it verifies for any of them (--signer pins one).
        if [ -n "$SIGNER" ]; then
            principals=$SIGNER
        else
            principals=$(awk '!/^#/ && NF {print $1}' "$SIGNERS" | sort -u)
        fi
        if [ -z "$principals" ]; then
            bad "no principal found in $SIGNERS"
        else
            verified=0
            for p in $principals; do
                if ssh-keygen -Y verify -f "$SIGNERS" -I "$p" \
                        -n "$NAMESPACE" -s "$SIG" < "$MANIFEST" >/dev/null 2>&1; then
                    verified=1
                    break
                fi
            done
            [ "$verified" -eq 1 ] || bad "manifest signature INVALID for every listed principal"
        fi
    fi
fi

if [ "$fail" -ne 0 ]; then
    say "RESULT: FAILED ($level) — do not proceed under this bundle (Handshake.md §6)"
    exit 1
fi
say "RESULT: VERIFIED [$level] $declared_id"
exit 0
