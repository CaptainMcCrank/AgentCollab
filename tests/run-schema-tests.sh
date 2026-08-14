#!/bin/sh
# Schema lint tests: every fixture under tests/fixtures/valid/ must validate,
# every fixture under tests/fixtures/invalid/ must fail validation.
# Exit: 0 all pass · 1 any failure. Last line: RESULT pass=<n> fail=<n>

set -u
REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LINT="$REPO_DIR/bin/acp-lint.py"
pass=0; fail=0

command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }

for f in "$REPO_DIR"/tests/fixtures/valid/*; do
    if python3 "$LINT" "$f" >/dev/null 2>&1; then
        pass=$((pass+1)); printf 'PASS valid fixture accepted: %s\n' "$(basename "$f")"
    else
        fail=$((fail+1)); printf 'FAIL valid fixture rejected: %s\n' "$(basename "$f")"
        python3 "$LINT" "$f" 2>&1 | sed 's/^/    /'
    fi
done

for f in "$REPO_DIR"/tests/fixtures/invalid/*; do
    if python3 "$LINT" "$f" >/dev/null 2>&1; then
        fail=$((fail+1)); printf 'FAIL invalid fixture accepted: %s\n' "$(basename "$f")"
    else
        pass=$((pass+1)); printf 'PASS invalid fixture rejected: %s\n' "$(basename "$f")"
    fi
done

printf 'RESULT pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
