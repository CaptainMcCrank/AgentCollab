## CONFLICT 1
**Protocol:** AgentCollab/1.0.1#sha256:ecce17042a867fe9
**Claim A:** envelope says docs/GUIDE.md has six sections (envelope, Assumed pre-state)
**Claim B:** the file on disk has five sections (grep -c '^## ' docs/GUIDE.md)
**Ground truth check:** grep -c '^## ' docs/GUIDE.md returned 5
**Resolution:** RECONCILE — treat the file as ground truth; corrected the envelope claim in the session log and noted the missing section as open work
