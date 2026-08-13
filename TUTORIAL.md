# Tutorial: Two Agents on One Protocol

This tutorial shows you how to set up two AI agents that follow the AgentCollab protocol and prove to each other that they hold the same rules.

## Why this protocol exists

**Problem.** In June 2026, two of my coding agents edited the same repository during the same afternoon. Each session was blind to the other. The first agent left a handoff note which claimed that a configuration file was already in place. That claim was stale. The second agent trusted the note, built on top of the error, and the damage stayed hidden for days.

**Action.** I wrote the shared rules for agent collaboration into one document and published it as AgentCollab. The protocol includes a handshake. Each agent computes an identifier from the protocol files with a small script. When any byte in those files changes, the identifier changes with it. Agents exchange the identifier before the first edit, and a maintainer signature lets each agent confirm that its copy of the rules is authentic.

**Result.** A divergence now stops the session before an edit happens. Each agent can prove that it holds the same signed rules as its partner. A wrong claim in a handoff surfaces during the receiver's inventory step and becomes a recorded conflict.

## What you will build

Two agents that share one project:

- a writer agent that drafts a document and ends its session with a handoff envelope
- a reviewer agent that verifies the handshake, checks the envelope against the repository, and then edits

## What you need

- git and OpenSSH 8.1 or later (for `ssh-keygen`)
- `sha256sum`, part of GNU coreutils
- an agent runtime that accepts a prompt and can run shell commands, for example Claude Code
- an empty project directory
- about twenty minutes

## Step 1: Import the protocol and verify it

Run these commands in your project directory:

```sh
git init
git clone https://github.com/CaptainMcCrank/AgentCollab protocol-lib
./protocol-lib/bin/acp-verify.sh
```

The last command checks every protocol file against a signed manifest, and it checks the maintainer signature on the manifest itself. The expected output is one line:

```
acp-verify: RESULT: VERIFIED [L2] AgentCollab/1.0.1#sha256:ecce17042a867fe9
```

If you want a stricter check, compare the key in `protocol-lib/keys/allowed_signers` with the copy at <https://patrickmccanna.net/agentcollab>. That page lives on a domain that the repository does not control.

Now compute the protocol ID:

```sh
./protocol-lib/bin/acp-id.sh
```

Keep the output in view. Your two agents will exchange this exact string, and each agent must compute it with this script, because a language model cannot compute a hash in its head.

## Step 2: Bind the protocol to your project

The protocol names its tooling interfaces in the abstract, so each project declares where those interfaces live. Create a file named `PROFILE.md` in the project root:

```markdown
# AgentCollab Integration Profile — demo project
Protocol: <paste the output of ./protocol-lib/bin/acp-id.sh>

| Interface | Binding |
|---|---|
| work tracker | `WORK.md` table in the project root |
| session log | `logs/`, one markdown file per session |
| charter | `charters/`, one file per agent |
| decision record | `DECISIONS.md` |
| ground truth | this git repository |
```

Then create the empty surfaces:

```sh
mkdir logs charters
printf '| item | status | claimed_by |\n|---|---|---|\n' > WORK.md
touch DECISIONS.md
```

## Step 3: Give each agent a charter

A charter tells an agent what it owns and where its authority ends. Create `charters/writer.md`:

```yaml
agent_charter:
  version: 1.0
  id: writer-agent-v1.0
  specialization: >
    Drafting user documentation for this project.
  write_scopes:
    - "docs/**"
    - "logs/**"
    - "WORK.md"
  approval:
    autonomous: [draft and edit files under docs/, update WORK.md]
    overseer: []
    human: [delete any file, change any charter]
  handoff:
    on_exit: context_handoff
    on_receive: inventory_first
```

Create `charters/reviewer.md` with the same shape:

```yaml
agent_charter:
  version: 1.0
  id: reviewer-agent-v1.0
  specialization: >
    Reviewing documentation for accuracy and repairing the defects it finds.
  write_scopes:
    - "docs/**"
    - "logs/**"
    - "WORK.md"
  approval:
    autonomous: [edit files under docs/, update WORK.md]
    overseer: []
    human: [delete any file, change any charter]
  handoff:
    on_exit: context_handoff
    on_receive: inventory_first
```

## Step 4: Start the writer agent

Open your agent runtime in the project directory and give it this prompt:

```
Act as writer-agent-v1.0. Your charter is charters/writer.md.
Read protocol-lib/protocol/Agent_Collaboration_Protocol.md and PROFILE.md
before you do anything else.
Run ./protocol-lib/bin/acp-id.sh and keep the output.
Task: draft docs/GUIDE.md, a short getting-started guide for this project.
Record your work in WORK.md.
End the session with a CONTEXT-HANDOFF envelope. Write the envelope to
logs/ and print it. Put the script output in the Protocol field.
```

The agent drafts the document and closes with an envelope. The envelope looks like this:

```markdown
## CONTEXT-HANDOFF
**Protocol:** AgentCollab/1.0.1#sha256:ecce17042a867fe9
**From:** writer-agent-v1.0 · <model> · <timestamps>
**Banner:** First draft of GUIDE.md, ready for review

### What this session did
- Drafted docs/GUIDE.md (commit a1b2c3d)

### Assumed receiver pre-state — MUST VERIFY
- docs/GUIDE.md exists and has six sections
...
```

Treat every line under the pre-state heading as a claim for the next agent to check against the repository.

## Step 5: Start the reviewer agent

Open a fresh session in the same directory and give it this prompt:

```
Act as reviewer-agent-v1.0. Your charter is charters/reviewer.md.
Read protocol-lib/protocol/Agent_Collaboration_Protocol.md and PROFILE.md
before you do anything else.
Run ./protocol-lib/bin/acp-verify.sh, then ./protocol-lib/bin/acp-id.sh.
Compare your computed ID with the Protocol field of the latest envelope
in logs/. If the two strings differ, stop and report a CONFLICT.
Publish an INVENTORY report before any edit. Check every claim in the
envelope against the repository.
Task: review docs/GUIDE.md for accuracy and repair the defects you find.
Record your work in WORK.md.
End the session with your own CONTEXT-HANDOFF envelope in logs/.
```

Watch the first output of the session. Before the agent touches a file, it must print an inventory:

```markdown
## INVENTORY
**Protocol (recomputed):** AgentCollab/1.0.1#sha256:ecce17042a867fe9 [L2]
**Present:**   docs/GUIDE.md exists with six sections, as claimed
**Missing:**   none
**Divergent:** none
**Unclaimed:** an untracked scratch file at notes.tmp
```

The recomputed line matters most. The reviewer ran the script itself, so the match gives evidence about the files on disk. The protocol requires this recomputation because an echoed string would only show that the agent can copy text.

## Step 6: Break the handshake on purpose

A working failure is worth seeing once. Append a single space to one protocol file:

```sh
printf ' ' >> protocol-lib/protocol/Handshake.md
./protocol-lib/bin/acp-id.sh
./protocol-lib/bin/acp-verify.sh
```

The ID in the first output no longer matches any envelope in `logs/`, and the verify script reports FAIL against the signed manifest. Start the reviewer prompt again and it will refuse to edit, then record a conflict with both strings quoted. Repair the file when you finish:

```sh
git -C protocol-lib checkout .
```

## What the handshake proves

An ID match proves that both agents read byte-identical rule files. The signature check proves that those bytes came from the maintainer. Obedience is a separate question, because a model can hold correct rules and drift from them anyway. For conduct, read the session logs, where every envelope and every conflict record stays available for audit.

## Where to go next

- `protocol-lib/protocol/Handshake.md` §6 covers mismatch resolution between versions.
- `protocol-lib/adapters/README.md` shows bindings for GitHub Issues and other trackers.
- Wire `acp-verify.sh` into your runtime's session-start hook, and the handshake stops depending on the agent's willingness to run it.
- Pin the maintainer key from <https://patrickmccanna.net/agentcollab> before you trust a vendored copy.
