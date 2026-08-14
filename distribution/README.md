# Distribution — putting the protocol where agents load capabilities

Agents don't browse GitHub. This directory packages the protocol for the surfaces where agents and their frameworks actually acquire behavior.

| Artifact | For | Install |
|---|---|---|
| `claude-code-skill/agentcollab/` | Claude Code sessions | Copy the `agentcollab/` directory into `~/.claude/skills/` (all projects) or `<project>/.claude/skills/` (one project). The skill triggers on handoffs, envelopes, and handshake mentions. |
| `mcp/agentcollab_mcp.py` | Any MCP-capable agent, including shell-less runtimes | `claude mcp add agentcollab -- python3 /absolute/path/to/agentcollab_mcp.py` (or the equivalent registration in your MCP client). Serves `agentcollab_id`, `agentcollab_verify`, `agentcollab_lint`. Requires the full repo checkout (it imports `impl/`, `bin/`, `schemas/`). |
| `AGENTS-snippet.md` | Consuming projects' `AGENTS.md` / `CLAUDE.md` | Paste the block; adjust the bundle path. |
| `llms.txt` | The trust-anchor website | Upload to the site root as `llms.txt` (the [llms.txt convention](https://llmstxt.org/)) so agents crawling the domain find the protocol, the key, and the verification ritual. |

The skill and the snippet teach the *rules*; the MCP server supplies the *tools* (backed by the Python reference implementation, so no shell is needed); `llms.txt` closes the discovery loop from the trust-anchor domain. None of these files are part of the hashed bundle — updating them never changes the protocol ID.

Tested by `tests/run-mcp-tests.sh` (a scripted JSON-RPC session against the server), which runs in CI.
