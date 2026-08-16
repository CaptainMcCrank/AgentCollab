#!/bin/sh
# agentcollab-id.sh — compute the AgentCollab protocol ID from local bundle bytes.
#
# Reference implementation of Handshake.md §2–§3. Agents obtain the protocol
# ID by running this script; an ID not produced by a tool run is fabricated.
#
# Usage:
#   agentcollab-id.sh            print the protocol ID (from the manifest's file list)
#   agentcollab-id.sh --root     print the full 64-hex bundle root
#   agentcollab-id.sh --write    regenerate PROTOCOL_MANIFEST.yaml from local files
#                        (file list = protocol/*, version = VERSION file)
#
# Exit codes: 0 ok · 1 usage/environment error · 2 bundle file missing

set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT_DIR"
MANIFEST="PROTOCOL_MANIFEST.yaml"

die() { printf 'acp-id: %s\n' "$*" >&2; exit "${2:-1}"; }

command -v sha256sum >/dev/null 2>&1 || die "sha256sum not found"

# Print "<sha256>  <path>" lines, path-sorted (Handshake.md §2), for the paths on stdin.
hash_listing() {
    while IFS= read -r p; do
        [ -f "$p" ] || die "bundle file missing: $p" 2
        sha256sum "$p"
    done | LC_ALL=C sort -k 2
}

bundle_root() { hash_listing | sha256sum | cut -c1-64; }

manifest_paths() {
    [ -f "$MANIFEST" ] || die "$MANIFEST not found (run --write to create it)"
    awk '/^  - path: /{print $3}' "$MANIFEST"
}

case "${1:-}" in
    --write)
        [ -f VERSION ] || die "VERSION file not found"
        version=$(cat VERSION)
        paths=$(find protocol -type f | LC_ALL=C sort)
        [ -n "$paths" ] || die "no files under protocol/"
        root=$(printf '%s\n' "$paths" | bundle_root)
        id="AgentCollab/${version}#sha256:$(printf '%s' "$root" | cut -c1-16)"
        {
            printf 'protocol: AgentCollab\n'
            printf 'version: %s\n' "$version"
            printf 'hash_algorithm: sha256\n'
            printf 'files:\n'
            printf '%s\n' "$paths" | while IFS= read -r p; do
                printf '  - path: %s\n' "$p"
                printf '    sha256: %s\n' "$(sha256sum "$p" | cut -c1-64)"
            done
            printf 'bundle_root: %s\n' "$root"
            printf 'id: %s\n' "$id"
        } > "$MANIFEST"
        printf '%s\n' "$id"
        printf 'acp-id: wrote %s (%d files) — re-sign it: ssh-keygen -Y sign -f <key> -n agentcollab-manifest %s\n' \
            "$MANIFEST" "$(printf '%s\n' "$paths" | wc -l)" "$MANIFEST" >&2
        ;;
    --root)
        manifest_paths | bundle_root
        ;;
    '')
        version=$(awk '/^version: /{print $2; exit}' "$MANIFEST" 2>/dev/null) \
            || die "$MANIFEST not found"
        [ -n "$version" ] || die "no version in $MANIFEST"
        root=$(manifest_paths | bundle_root)
        printf 'AgentCollab/%s#sha256:%s\n' "$version" "$(printf '%s' "$root" | cut -c1-16)"
        ;;
    *)
        die "unknown option: $1 (usage: agentcollab-id.sh [--root|--write])"
        ;;
esac
