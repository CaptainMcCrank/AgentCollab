# Charter: reviewer-agent-v1.0

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
