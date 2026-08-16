#!/bin/sh
# Compatibility alias — the canonical name is agentcollab-id.sh (renamed in
# v1.1.0 to avoid the "ACP" collision with the Agent Communication Protocol).
exec "$(dirname -- "$0")/agentcollab-id.sh" "$@"
