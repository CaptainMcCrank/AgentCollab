Act as reviewer-agent-v1.0. Your charter is charters/reviewer.md.
Read protocol-lib/protocol/Agent_Collaboration_Protocol.md and PROFILE.md
before you do anything else.
Run ./protocol-lib/bin/acp-verify.sh, then ./protocol-lib/bin/acp-id.sh.
Compare your computed ID with the Protocol field of the latest envelope
in logs/. If the two strings differ, stop and report a CONFLICT.
Publish an INVENTORY report before any edit. Check every claim in the
envelope against the workspace.
Task: review docs/GUIDE.md for accuracy and repair the defects you find.
Record your work in WORK.md.
End the session with your own CONTEXT-HANDOFF envelope in logs/.
