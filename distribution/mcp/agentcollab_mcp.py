#!/usr/bin/env python3
"""agentcollab_mcp.py — MCP (Model Context Protocol) server for AgentCollab.

Exposes the handshake as MCP tools so any MCP-capable agent — including agents
with no shell access — can compute and verify protocol IDs natively:

  agentcollab_id      compute the protocol ID from a local bundle
  agentcollab_verify  verify a bundle (L1 integrity; L2 authenticity)
  agentcollab_lint    validate protocol blocks in a file against schemas/

Transport: stdio, newline-delimited JSON-RPC 2.0 (the MCP stdio framing).
Standard library only; embeds impl/python/agentcollab.py and bin/agentcollab-lint.py.

Register with Claude Code:
  claude mcp add agentcollab -- python3 /absolute/path/to/agentcollab_mcp.py

Exit codes: 0 clean shutdown (stdin closed) · 2 environment error
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SERVER_INFO = {"name": "agentcollab", "version": (REPO / "VERSION").read_text().strip()}


def _load(name, rel_path):
    spec = importlib.util.spec_from_file_location(name, REPO / rel_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


core = _load("agentcollab_core", "impl/python/agentcollab.py")

TOOLS = [
    {
        "name": "agentcollab_id",
        "description": (
            "Compute the AgentCollab protocol ID from a local protocol bundle. "
            "Call this to fill the Protocol field of any labeled block, and to "
            "recompute the ID during the receiver handshake — never echo a "
            "counterparty's ID or recall one from memory."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {
                    "type": "string",
                    "description": "Directory containing PROTOCOL_MANIFEST.yaml "
                                   "(the bundle root, e.g. ./protocol-lib)",
                },
            },
            "required": ["root"],
        },
    },
    {
        "name": "agentcollab_verify",
        "description": (
            "Verify an AgentCollab protocol bundle. Call this before the first "
            "mutation in any session that received a handoff. L2 (default) checks "
            "file integrity against the signed manifest AND the maintainer "
            "signature; no_sig=true checks integrity only (L1)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "root": {
                    "type": "string",
                    "description": "Directory containing PROTOCOL_MANIFEST.yaml",
                },
                "no_sig": {
                    "type": "boolean",
                    "description": "Skip the signature check (L1 integrity only)",
                },
            },
            "required": ["root"],
        },
    },
    {
        "name": "agentcollab_lint",
        "description": (
            "Validate the AgentCollab protocol blocks in a file (CONTEXT-HANDOFF, "
            "INVENTORY, CONFLICT, DELEGATE, USER-HANDOFF, agent_charter) against "
            "the protocol's JSON Schemas. Use it to check an envelope or report "
            "before publishing it."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File to validate"},
            },
            "required": ["path"],
        },
    },
]


def tool_id(args):
    return core.protocol_id(args["root"]), False


def tool_verify(args):
    check_sig = not args.get("no_sig", False)
    ok, level, errors = core.verify(args["root"], check_sig=check_sig)
    if ok:
        return f"VERIFIED [{level}] {core.protocol_id(args['root'])}", False
    lines = [f"FAILED ({level}) — do not proceed under this bundle (Handshake.md §6)"]
    lines += [f"  {e}" for e in errors]
    return "\n".join(lines), True


def tool_lint(args):
    lint = _load("acp_lint", "bin/agentcollab-lint.py")
    text = Path(args["path"]).read_text()
    blocks = []
    if "agent_charter" in text:
        charter = lint.parse_charter(text)
        if charter is not None:
            blocks.append(("agent-charter", charter))
    for ctype, lines in lint.split_blocks(text):
        blocks.append((ctype, lint.PARSERS[ctype](lines)))
    if not blocks:
        return "no recognized protocol blocks found", True
    out, failed = [], False
    for ctype, instance in blocks:
        schema = json.loads((REPO / "schemas" / f"{ctype}.schema.json").read_text())
        errs = lint.validate(instance, schema)
        if errs:
            failed = True
            out.append(f"INVALID {ctype}")
            out += [f"  {e}" for e in errs]
        else:
            out.append(f"VALID   {ctype}")
    return "\n".join(out), failed


HANDLERS = {
    "agentcollab_id": tool_id,
    "agentcollab_verify": tool_verify,
    "agentcollab_lint": tool_lint,
}

# ------------------------------ JSON-RPC loop --------------------------------


def reply(msg_id, result=None, error=None):
    payload = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def handle(msg):
    method = msg.get("method")
    msg_id = msg.get("id")
    if method == "initialize":
        reply(msg_id, {
            "protocolVersion": msg.get("params", {}).get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })
    elif method == "notifications/initialized":
        pass  # notification: no response
    elif method == "ping":
        reply(msg_id, {})
    elif method == "tools/list":
        reply(msg_id, {"tools": TOOLS})
    elif method == "tools/call":
        params = msg.get("params", {})
        handler = HANDLERS.get(params.get("name"))
        if handler is None:
            reply(msg_id, error={"code": -32602, "message": f"unknown tool: {params.get('name')}"})
            return
        try:
            text, is_error = handler(params.get("arguments", {}))
        except Exception as exc:  # tool errors are results, not protocol errors
            text, is_error = f"{type(exc).__name__}: {exc}", True
        reply(msg_id, {"content": [{"type": "text", "text": text}], "isError": is_error})
    elif msg_id is not None:
        reply(msg_id, error={"code": -32601, "message": f"method not found: {method}"})


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            sys.stderr.write("agentcollab-mcp: skipping non-JSON line\n")
            continue
        handle(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
