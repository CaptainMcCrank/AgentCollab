#!/usr/bin/env python3
"""run.py — AgentCollab conformance runner and grader.

The grader is deterministic and LLM-free: it validates the labeled blocks a
subject emitted (via schemas/ and bin/acp-lint.py) and diffs the workspace
against the snapshot taken at prepare time. The subject — the agent under
test — runs separately, between `prepare` and `grade`.

Usage:
  run.py list
  run.py prepare <scenario-id> --dir DIR    materialize the scenario workspace
  run.py grade --dir DIR                    grade OUTPUT.md + workspace changes

Flow: prepare → start your agent in DIR with the prompt in PROMPT.md → save
the agent's complete session output to DIR/OUTPUT.md → grade.

Exit codes: 0 scenario passed · 1 failed · 2 usage/environment error
"""
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS = Path(__file__).resolve().parent / "scenarios"
BASE = Path(__file__).resolve().parent / "base-workspace"
WRONG_ID = "AgentCollab/9.9.9#sha256:deadbeefdeadbeef"
BUNDLE_ITEMS = ["protocol", "bin", "keys", "PROTOCOL_MANIFEST.yaml",
                "PROTOCOL_MANIFEST.yaml.sig", "VERSION"]
# Paths a subject may legitimately write during any scenario:
DIFF_EXCLUDE = ("OUTPUT.md", ".conformance/*", "logs/*", "WORK.md")

def die(msg, code=2):
    sys.stderr.write(f"conformance: {msg}\n")
    sys.exit(code)

def load_lint():
    spec = importlib.util.spec_from_file_location("acp_lint", ROOT / "bin" / "acp-lint.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def scenario_dir(sid):
    for d in sorted(SCENARIOS.iterdir()):
        if d.name.split("-")[0] == sid or d.name == sid:
            return d
    die(f"unknown scenario '{sid}' (run.py list)")

def load_scenario(d):
    import yaml
    return yaml.safe_load((d / "scenario.yaml").read_text())

def compute_id(workspace):
    r = subprocess.run(["./bin/acp-id.sh"], cwd=workspace / "protocol-lib",
                       capture_output=True, text=True)
    if r.returncode != 0:
        die(f"acp-id.sh failed in workspace bundle: {r.stderr.strip()}")
    return r.stdout.strip().splitlines()[0]

def tree_hashes(workspace):
    out = {}
    for p in sorted(workspace.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(workspace).as_posix()
        if rel.startswith("protocol-lib/") or any(fnmatch(rel, pat) for pat in DIFF_EXCLUDE):
            continue
        out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out

# ------------------------------ prepare --------------------------------------

def prepare(sid, target):
    d = scenario_dir(sid)
    scen = load_scenario(d)
    target = Path(target)
    if target.exists() and any(target.iterdir()):
        die(f"target {target} exists and is not empty")
    shutil.copytree(BASE, target, dirs_exist_ok=True)
    overlay = d / "workspace"
    if overlay.exists():
        shutil.copytree(overlay, target, dirs_exist_ok=True)
    lib = target / "protocol-lib"
    lib.mkdir()
    for item in BUNDLE_ITEMS:
        src = ROOT / item
        if src.is_dir():
            shutil.copytree(src, lib / item)
        else:
            shutil.copy2(src, lib / item)
    for sh in (lib / "bin").glob("*.sh"):
        sh.chmod(0o755)
    pid = compute_id(target)
    for p in target.rglob("*"):
        if p.is_file() and not p.relative_to(target).as_posix().startswith("protocol-lib/"):
            try:
                text = p.read_text()
            except UnicodeDecodeError:
                continue
            if "{{PROTOCOL_ID}}" in text or "{{WRONG_ID}}" in text:
                p.write_text(text.replace("{{PROTOCOL_ID}}", pid).replace("{{WRONG_ID}}", WRONG_ID))
    meta_dir = target / ".conformance"
    meta_dir.mkdir()
    (meta_dir / "meta.json").write_text(json.dumps({
        "scenario": d.name, "id": scen["id"], "protocol_id": pid,
        "baseline": tree_hashes(target),
    }, indent=2))
    print(f"prepared {scen['id']} ({scen['title']}) in {target}")
    print(f"next: run your agent in {target} with the prompt in PROMPT.md,")
    print(f"save its complete session output to {target}/OUTPUT.md, then:")
    print(f"  run.py grade --dir {target}")

# ------------------------------ grade ----------------------------------------

def parse_output(lint, text):
    blocks = []
    for ctype, lines in lint.split_blocks(text):
        blocks.append((ctype, lint.PARSERS[ctype](lines)))
    return blocks

def first_valid(lint, blocks, btype):
    schema = json.loads((ROOT / "schemas" / f"{btype}.schema.json").read_text())
    for ctype, inst in blocks:
        if ctype == btype and not lint.validate(inst, schema):
            return inst
    return None

def grade(target):
    lint = load_lint()
    target = Path(target)
    meta_path = target / ".conformance" / "meta.json"
    if not meta_path.exists():
        die(f"{target} was not prepared by this runner (no .conformance/meta.json)")
    meta = json.loads(meta_path.read_text())
    scen = load_scenario(SCENARIOS / meta["scenario"])
    out_path = target / "OUTPUT.md"
    if not out_path.exists():
        die(f"no OUTPUT.md in {target} — save the subject's session output there first")
    # The protocol's own D4 makes the session log the durable home of protocol
    # records, so grading reads the subject's NEW session-log files (in name
    # order) ahead of OUTPUT.md. Files that shipped with the scenario are the
    # sender's, not the subject's, and are excluded.
    shipped = {p.name for src in (BASE, SCENARIOS / meta["scenario"] / "workspace")
               if (src / "logs").is_dir() for p in (src / "logs").iterdir()}
    new_logs = sorted(p for p in (target / "logs").glob("*")
                      if p.is_file() and p.name not in shipped)
    text = "\n\n".join([p.read_text() for p in new_logs] + [out_path.read_text()])
    blocks = parse_output(lint, text)
    current = tree_hashes(target)
    baseline = meta["baseline"]

    results = []
    for exp in scen["expect"]:
        kind = exp["type"]
        ok, detail = False, ""
        if kind == "first_block":
            ok = bool(blocks) and blocks[0][0] == exp["block"]
            detail = f"first block is {blocks[0][0] if blocks else 'none'}"
        elif kind == "block_valid":
            ok = first_valid(lint, blocks, exp["block"]) is not None
            detail = f"schema-valid {exp['block']} block {'found' if ok else 'not found'}"
        elif kind == "block_absent":
            ok = all(ctype != exp["block"] for ctype, _ in blocks)
            detail = f"{exp['block']} block {'absent' if ok else 'present'}"
        elif kind in ("field_matches", "field_not_matches"):
            inst = first_valid(lint, blocks, exp["block"]) or next(
                (i for c, i in blocks if c == exp["block"]), None)
            val = "" if inst is None else str(inst.get(exp["field"], ""))
            hit = bool(re.search(exp["pattern"], val))
            ok = hit if kind == "field_matches" else (inst is not None and not hit)
            detail = f"{exp['block']}.{exp['field']} = {val[:60]!r}"
        elif kind == "recomputed_id":
            inst = first_valid(lint, blocks, "inventory") or next(
                (i for c, i in blocks if c == "inventory"), None)
            val = "" if inst is None else inst.get("protocol_recomputed", "")
            lead = re.match(r"^(\S+)", val)
            ok = bool(lead) and lead.group(1) == meta["protocol_id"]
            detail = f"inventory declares {val!r}, bundle computes {meta['protocol_id']!r}"
        elif kind == "no_change":
            pat = exp["path"]
            changed = [p for p, h in baseline.items()
                       if fnmatch(p, pat) and current.get(p) != h]
            added = [p for p in current if p not in baseline and fnmatch(p, pat)]
            ok = not changed and not added
            detail = f"changed={changed or 'none'} added={added or 'none'}"
        elif kind == "output_matches":
            ok = bool(re.search(exp["pattern"], text))
            detail = f"pattern /{exp['pattern']}/"
        elif kind == "output_not_matches":
            ok = not re.search(exp["pattern"], text)
            detail = f"pattern /{exp['pattern']}/"
        else:
            die(f"unknown expectation type '{kind}' in {meta['scenario']}")
        results.append((ok, kind, detail))

    print(f"scenario {scen['id']} — {scen['title']}  (rules: {scen['rules']})")
    for ok, kind, detail in results:
        print(f"  {'PASS' if ok else 'FAIL'} {kind}: {detail}")
    verdict = all(ok for ok, _, _ in results)
    print(f"VERDICT: {'PASS' if verdict else 'FAIL'} "
          f"({sum(ok for ok, _, _ in results)}/{len(results)} checks)")
    return 0 if verdict else 1

# ------------------------------ cli ------------------------------------------

def main(argv):
    if not argv:
        sys.stderr.write(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "list":
        for d in sorted(SCENARIOS.iterdir()):
            s = load_scenario(d)
            print(f"{s['id']}  {s['title']}  (rules {s['rules']})")
        return 0
    if cmd == "prepare":
        if len(argv) < 4 or argv[2] != "--dir":
            die("usage: run.py prepare <scenario-id> --dir DIR")
        prepare(argv[1], argv[3])
        return 0
    if cmd == "grade":
        if len(argv) < 3 or argv[1] != "--dir":
            die("usage: run.py grade --dir DIR")
        return grade(argv[2])
    die(f"unknown command '{cmd}'")

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
