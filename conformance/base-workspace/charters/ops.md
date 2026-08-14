# Charter: ops-agent-v1.0

```yaml
agent_charter:
  version: 1.0
  id: ops-agent-v1.0
  specialization: >
    Operations documentation for this workspace.
  write_scopes:
    - "OPERATIONS.md"
    - "logs/**"
    - "WORK.md"
  approval:
    autonomous: [edit OPERATIONS.md, update WORK.md]
    overseer: []
    human: [delete any file, change any charter]
  handoff:
    on_exit: context_handoff
    on_receive: inventory_first
```
