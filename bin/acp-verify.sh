#!/bin/sh
# Compatibility alias — the canonical name is agentcollab-verify.sh (renamed in
# v1.1.0 to avoid the "ACP" collision with the Agent Communication Protocol).
exec "$(dirname -- "$0")/agentcollab-verify.sh" "$@"
