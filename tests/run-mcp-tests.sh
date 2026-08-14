#!/bin/sh
# MCP server test: drive distribution/mcp/agentcollab_mcp.py through a scripted
# JSON-RPC session — initialize, tools/list, and one tools/call per tool,
# including failure paths. No MCP client library needed.
# Exit: 0 all pass · 1 any failure. Last line: RESULT pass=<n> fail=<n>

set -u
REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SERVER="$REPO/distribution/mcp/agentcollab_mcp.py"
W=$(mktemp -d); trap 'rm -rf "$W"' EXIT
pass=0; fail=0
ok() { pass=$((pass+1)); printf 'PASS %s\n' "$1"; }
ko() { fail=$((fail+1)); printf 'FAIL %s\n' "$1"; }

command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }

# A tampered bundle copy for the failure-path checks
mkdir -p "$W/bad/protocol" "$W/bad/keys"
cp "$REPO/PROTOCOL_MANIFEST.yaml" "$REPO/PROTOCOL_MANIFEST.yaml.sig" "$REPO/VERSION" "$W/bad/"
cp -R "$REPO/protocol/." "$W/bad/protocol/"
cp "$REPO/keys/allowed_signers" "$W/bad/keys/"
printf ' ' >> "$W/bad/protocol/Handshake.md"

# Scripted session: one JSON-RPC message per line
cat > "$W/session.jsonl" <<EOF
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"agentcollab_id","arguments":{"root":"$REPO"}}}
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"agentcollab_verify","arguments":{"root":"$REPO"}}}
{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"agentcollab_verify","arguments":{"root":"$W/bad"}}}
{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"agentcollab_lint","arguments":{"path":"$REPO/tests/fixtures/valid/inventory.md"}}}
{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"agentcollab_lint","arguments":{"path":"$REPO/tests/fixtures/invalid/conflict-bad-resolution.md"}}}
{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"nonexistent_tool","arguments":{}}}
EOF

python3 "$SERVER" < "$W/session.jsonl" > "$W/out.jsonl" 2>"$W/err.log"
[ $? -eq 0 ] && ok "server ran the session and exited cleanly" || ko "server exited nonzero ($(cat "$W/err.log"))"

python3 - "$W/out.jsonl" "$REPO" <<'EOF'
import json, subprocess, sys
out_path, repo = sys.argv[1], sys.argv[2]
resp = {}
for line in open(out_path):
    msg = json.loads(line)
    resp[msg["id"]] = msg
passed = failed = 0
def check(name, cond):
    global passed, failed
    print(("PASS " if cond else "FAIL ") + name)
    passed, failed = passed + (1 if cond else 0), failed + (0 if cond else 1)

check("initialize returns serverInfo + tools capability",
      resp[1]["result"]["serverInfo"]["name"] == "agentcollab"
      and "tools" in resp[1]["result"]["capabilities"])
names = [t["name"] for t in resp[2]["result"]["tools"]]
check("tools/list exposes the three tools",
      names == ["agentcollab_id", "agentcollab_verify", "agentcollab_lint"])
shell_id = subprocess.run([f"{repo}/bin/acp-id.sh"], cwd=repo,
                          capture_output=True, text=True).stdout.strip()
check("agentcollab_id matches the shell reference",
      resp[3]["result"]["content"][0]["text"] == shell_id
      and not resp[3]["result"]["isError"])
check("agentcollab_verify passes on the real bundle at L2",
      "VERIFIED [L2]" in resp[4]["result"]["content"][0]["text"]
      and not resp[4]["result"]["isError"])
check("agentcollab_verify fails on a tampered bundle with isError",
      resp[5]["result"]["isError"]
      and "FAILED" in resp[5]["result"]["content"][0]["text"])
check("agentcollab_lint accepts a valid block",
      "VALID" in resp[6]["result"]["content"][0]["text"]
      and not resp[6]["result"]["isError"])
check("agentcollab_lint rejects an invalid block with isError",
      resp[7]["result"]["isError"]
      and "INVALID" in resp[7]["result"]["content"][0]["text"])
check("unknown tool returns a JSON-RPC error", "error" in resp[8])
print(f"RESULT pass={passed+1} fail={failed}")  # +1 for the shell-level exit check
sys.exit(1 if failed else 0)
EOF
rc=$?
[ "$fail" -eq 0 ] && [ "$rc" -eq 0 ]
