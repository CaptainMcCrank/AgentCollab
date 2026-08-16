#!/usr/bin/env python3
"""Compatibility alias — the canonical name is agentcollab-lint.py (renamed in
v1.1.0 to avoid the "ACP" collision with the Agent Communication Protocol)."""
import os
import sys

os.execv(sys.executable, [
    sys.executable,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "agentcollab-lint.py"),
    *sys.argv[1:],
])
