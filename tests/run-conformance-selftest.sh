#!/bin/sh
# Grader self-test: every reference transcript must PASS its scenario, and
# two deliberately broken runs must FAIL. No LLM involved — this proves the
# grading mechanism, not any subject.
# Exit: 0 all pass · 1 any failure. Last line: RESULT pass=<n> fail=<n>

set -u
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RUN="$REPO/conformance/run.py"
pass=0; fail=0

command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }

run_case() { # run_case <name> <expected-exit> <actual-exit>
    if [ "$2" -eq "$3" ]; then
        pass=$((pass+1)); printf 'PASS %s\n' "$1"
    else
        fail=$((fail+1)); printf 'FAIL %s (expected exit %s, got %s)\n' "$1" "$2" "$3"
    fi
}

fill() { # fill <workspace> <transcript>
    pid=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['protocol_id'])" "$1/.conformance/meta.json")
    sed "s|{{PROTOCOL_ID}}|$pid|g" "$2" > "$1/OUTPUT.md"
}

W=$(mktemp -d); trap 'rm -rf "$W"' EXIT

for d in "$REPO"/conformance/scenarios/*/; do
    sid=$(basename "$d" | cut -d- -f1)
    ws="$W/$sid"
    python3 "$RUN" prepare "$sid" --dir "$ws" >/dev/null || { echo "prepare $sid failed"; exit 1; }
    fill "$ws" "$REPO/conformance/transcripts/$sid.md"
    python3 "$RUN" grade --dir "$ws" >"$W/$sid.log" 2>&1
    rc=$?
    run_case "reference transcript passes $sid" 0 "$rc"
    [ "$rc" -ne 0 ] && sed 's/^/    /' "$W/$sid.log"
done

# Session-log grading: blocks written to logs/ (per control D4) count even
# when OUTPUT.md is empty — the claude -p final-message-only case.
ws="$W/logsgrade"
python3 "$RUN" prepare S02 --dir "$ws" >/dev/null
pid=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['protocol_id'])" "$ws/.conformance/meta.json")
sed "s|{{PROTOCOL_ID}}|$pid|g" "$REPO/conformance/transcripts/S02.md" > "$ws/logs/2026-08-13_reviewer-session.md"
: > "$ws/OUTPUT.md"
python3 "$RUN" grade --dir "$ws" >/dev/null 2>&1
run_case "blocks in session log grade without OUTPUT.md content" 0 $?

# Negative 1: blockless output must fail S01
ws="$W/neg1"
python3 "$RUN" prepare S01 --dir "$ws" >/dev/null
printf 'I looked around and everything seemed fine, so I edited the guide.\n' > "$ws/OUTPUT.md"
python3 "$RUN" grade --dir "$ws" >/dev/null 2>&1
run_case "blockless output fails S01" 1 $?

# Negative 2: a workspace mutation must fail S03's no-mutation rule
ws="$W/neg2"
python3 "$RUN" prepare S03 --dir "$ws" >/dev/null
fill "$ws" "$REPO/conformance/transcripts/S03.md"
printf '\nedited anyway\n' >> "$ws/docs/GUIDE.md"
python3 "$RUN" grade --dir "$ws" >/dev/null 2>&1
run_case "mutation during S03 fails no_change" 1 $?

printf 'RESULT pass=%d fail=%d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
