#!/usr/bin/env python3
"""agentcollab-lint.py — validate AgentCollab protocol blocks against schemas/.

Parses the markdown block formats defined in protocol/Agent_Collaboration_Protocol.md
(and the YAML agent_charter block from protocol/Agent_Charter.md) into JSON, then
validates against the corresponding JSON Schema. The schemas are standard JSON
Schema; validation here uses a built-in checker covering the subset they use
(type, required, properties, items, enum, pattern, minItems, minLength), so the
only dependency is PyYAML, and only for charters.

Usage:
  agentcollab-lint.py FILE [FILE ...]      validate every recognized block in each file
  agentcollab-lint.py --json FILE          print parsed JSON for each block, then validate

Exit codes: 0 all blocks valid · 1 any invalid or no blocks found · 2 usage/environment
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"

BLOCK_HEADINGS = {
    "CONTEXT-HANDOFF": "context-handoff",
    "INVENTORY": "inventory",
    "CONFLICT": "conflict",
    "DELEGATE": "delegate",
    "USER-HANDOFF": "user-handoff",
}

# --------------- minimal JSON Schema validation (documented subset) ----------

def validate(instance, schema, path="$"):
    errs = []
    t = schema.get("type")
    if t:
        pytypes = {"object": dict, "array": list, "string": str,
                   "number": (int, float), "integer": int}[t]
        if not isinstance(instance, pytypes) or isinstance(instance, bool):
            errs.append(f"{path}: expected {t}, got {type(instance).__name__}")
            return errs
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not one of {schema['enum']}")
    if "pattern" in schema and isinstance(instance, str) and not re.search(schema["pattern"], instance):
        errs.append(f"{path}: {instance!r} does not match /{schema['pattern']}/")
    if "minLength" in schema and isinstance(instance, str) and len(instance) < schema["minLength"]:
        errs.append(f"{path}: shorter than minLength {schema['minLength']}")
    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errs.append(f"{path}: missing required field '{req}'")
        for key, sub in schema.get("properties", {}).items():
            if key in instance:
                errs += validate(instance[key], sub, f"{path}.{key}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        for i, item in enumerate(instance):
            if "items" in schema:
                errs += validate(item, schema["items"], f"{path}[{i}]")
    return errs

# --------------- markdown parsing helpers ------------------------------------

FIELD_RE = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")

def split_blocks(text):
    """Yield (block_type, lines) for each recognized '## ' block in the text."""
    lines = text.splitlines()
    current, ctype = None, None
    for line in lines:
        m = re.match(r"^##\s+(.*)$", line)
        if m and not line.startswith("###"):
            if current is not None:
                yield ctype, current
                current, ctype = None, None
            head = m.group(1).strip()
            for name, slug in BLOCK_HEADINGS.items():
                if head == name or head.startswith(name + " ") or head.startswith(name + " "):
                    current, ctype = [], slug
                    break
            continue
        if current is not None:
            current.append(line)
    if current is not None:
        yield ctype, current

def parse_fields(lines):
    """Collect '**Name:** value' fields; continuation lines append to the last field."""
    fields, order, last = {}, [], None
    for line in lines:
        if line.startswith("###") or line.startswith("|") or line.strip() == "---":
            last = None
            continue
        m = FIELD_RE.match(line.strip())
        if m:
            key = re.sub(r"[^a-z0-9]+", "_", m.group(1).strip().lower()).strip("_")
            fields[key] = m.group(2).strip()
            order.append(key)
            last = key
        elif last and line.strip():
            fields[last] = (fields[last] + "\n" + line.strip()).strip()
    return fields

def section_key(heading):
    head = re.split(r"—|--", heading)[0]  # drop '— MUST VERIFY' style suffixes
    return re.sub(r"[^a-z0-9]+", "_", head.strip().lower()).strip("_")

def parse_sections(lines):
    """Collect '### Heading' sections as arrays of their non-empty lines."""
    sections, current = {}, None
    for line in lines:
        m = re.match(r"^###\s+(.*)$", line)
        if m:
            current = section_key(m.group(1))
            sections[current] = []
        elif current is not None and line.strip():
            if FIELD_RE.match(line.strip()) and not sections[current]:
                current = None  # stray field after sections ended
            else:
                sections[current].append(line.strip())
    return sections

# --------------- per-block parsers -------------------------------------------

def parse_context_handoff(lines):
    head = [l for l in lines if not l.startswith("###")]
    fields = parse_fields(head[: next((i for i, l in enumerate(lines) if l.startswith("###")), len(lines))])
    return {
        "protocol": fields.get("protocol", ""),
        "from": fields.get("from", ""),
        "banner": fields.get("banner", ""),
        "sections": parse_sections(lines),
    }

def parse_inventory(lines):
    return parse_fields(lines)

def parse_conflict(lines):
    return parse_fields(lines)

def parse_delegate(lines):
    fields = parse_fields(lines)
    src = fields.pop("from", "")
    m = re.match(r"^(.*?)\s*→\s*\*\*To:\*\*\s*(.*)$", src)
    if m:
        fields["from"], fields["to"] = m.group(1).strip(), m.group(2).strip()
    else:
        fields["from"] = src
    return fields

def parse_user_handoff(lines):
    artifacts, primer, in_primer = [], [], False
    other = []
    for line in lines:
        s = line.strip()
        if s.startswith("**To start"):
            in_primer = True
            continue
        if in_primer:
            if s:
                primer.append(s)
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) == 3 and cells[0] not in ("Artifact", "") and not set(cells[1]) <= {"-"}:
                artifacts.append({"artifact": cells[0].strip("`"), "sha256": cells[1], "commit": cells[2]})
            continue
        other.append(line)
    fields = parse_fields(other)
    return {
        "protocol": fields.get("protocol", ""),
        "completed": fields.get("completed", ""),
        "artifacts": artifacts,
        "open_work": fields.get("open_work", ""),
        "primer": "\n".join(primer),
    }

PARSERS = {
    "context-handoff": parse_context_handoff,
    "inventory": parse_inventory,
    "conflict": parse_conflict,
    "delegate": parse_delegate,
    "user-handoff": parse_user_handoff,
}

def parse_charter(text):
    try:
        import yaml
    except ImportError:
        sys.stderr.write("acp-lint: charter validation needs PyYAML (pip install pyyaml)\n")
        sys.exit(2)
    fence = re.search(r"```yaml\s*\n(.*?)```", text, re.S)
    doc = yaml.safe_load(fence.group(1) if fence else text)
    if not isinstance(doc, dict) or "agent_charter" not in doc:
        return None
    return doc["agent_charter"]

# --------------- driver -------------------------------------------------------

def load_schema(slug):
    return json.loads((SCHEMAS / f"{slug}.schema.json").read_text())

def main(argv):
    dump = "--json" in argv
    paths = [a for a in argv if not a.startswith("--")]
    if not paths:
        sys.stderr.write(__doc__)
        return 2
    found, failed = 0, 0
    for p in paths:
        text = Path(p).read_text()
        blocks = []
        if "agent_charter" in text:
            charter = parse_charter(text)
            if charter is not None:
                blocks.append(("agent-charter", charter))
        for ctype, lines in split_blocks(text):
            blocks.append((ctype, PARSERS[ctype](lines)))
        for ctype, instance in blocks:
            found += 1
            if dump:
                print(json.dumps({"type": ctype, "parsed": instance}, indent=2, ensure_ascii=False))
            errs = validate(instance, load_schema(ctype))
            label = f"{p}: {ctype}"
            if errs:
                failed += 1
                print(f"INVALID {label}")
                for e in errs:
                    print(f"  {e}")
            else:
                print(f"VALID   {label}")
    if found == 0:
        sys.stderr.write("acp-lint: no recognized protocol blocks found\n")
        return 1
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
