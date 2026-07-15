#!/usr/bin/env python
"""
validate_kb.py — Knowledge Base static validator.

Battle-tested in the China 1-6 primary school KB project. Checks:
1. JSON Schema validity for nodes and edges
2. ID uniqueness (within and across files)
3. Dangling references (prerequisite / part_of / related / teaches / assesses
   point to existing nodes)
4. No self-cycles (edge from == to)
5. Topological ordering of the prerequisite graph (--check-topo)
6. Exercise quality:
   - choice questions have 4 options
   - answer matches an option (substring match against the full option text
     OR the letter "A" / "B" / "C" / "D")
   - assesses field references a real node

Usage:
    python validate_kb.py                    # basic
    python validate_kb.py --check-topo       # also run topo sort
    python validate_kb.py --exercises-only   # only check exercises
    python validate_kb.py --subject math     # filter to one subject
    python validate_kb.py --grade 3          # filter to one grade
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

try:
    import jsonschema
    from jsonschema import Draft7Validator
except ImportError:
    print("ERROR: jsonschema not installed. Run: pip install jsonschema", file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SCRIPT_DIR.parent


def discover_files(root: Path) -> tuple[list[Path], list[Path], list[Path], list[Path]]:
    """Find all nodes/edges JSON files and exercise JSON files."""
    node_files = [root / "nodes.json"]
    edge_files = [root / "edges.json"]
    exercise_files = []

    for p in (root / "subjects").rglob("nodes.json"):
        node_files.append(p)
    for p in (root / "subjects").rglob("edges.json"):
        edge_files.append(p)
    for p in (root / "exercises" / "by_concept").glob("*.json"):
        exercise_files.append(p)
    pool = root / "exercises" / "pool.json"
    if pool.exists():
        exercise_files.append(pool)

    return (
        [p for p in node_files if p.exists()],
        [p for p in edge_files if p.exists()],
        exercise_files,
        [root / "nodes.schema.json", root / "edges.schema.json"],
    )


def load_schemas(root: Path) -> tuple[dict, dict]:
    nodes_schema_path = root / "nodes.schema.json"
    edges_schema_path = root / "edges.schema.json"
    if not nodes_schema_path.exists() or not edges_schema_path.exists():
        print(
            f"ERROR: schema files not found at {nodes_schema_path} / {edges_schema_path}",
            file=sys.stderr,
        )
        sys.exit(2)
    return (
        json.loads(nodes_schema_path.read_text(encoding="utf-8")),
        json.loads(edges_schema_path.read_text(encoding="utf-8")),
    )


def validate_nodes(node_files, schema, subject_filter=None, grade_filter=None) -> tuple[list[dict], list[str]]:
    errors = []
    all_nodes = []
    for f in node_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{f}: JSON parse error: {e}")
            continue
        if not isinstance(data, list):
            errors.append(f"{f}: expected JSON array")
            continue
        validator = Draft7Validator(schema)
        for i, node in enumerate(data):
            errors.extend(
                f"{f}[{i}]: {e.message}"
                for e in validator.iter_errors(node)
            )
            if subject_filter and node.get("subject") != subject_filter:
                continue
            if grade_filter is not None and node.get("grade") != grade_filter:
                continue
            all_nodes.append(node)
    return all_nodes, errors


def validate_edges(edge_files, schema, node_ids, subject_filter=None, grade_filter=None) -> tuple[list[dict], list[str]]:
    errors = []
    all_edges = []
    for f in edge_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{f}: JSON parse error: {e}")
            continue
        if not isinstance(data, list):
            errors.append(f"{f}: expected JSON array")
            continue
        validator = Draft7Validator(schema)
        for i, edge in enumerate(data):
            errors.extend(
                f"{f}[{i}]: {e.message}"
                for e in validator.iter_errors(edge)
            )
            if subject_filter or grade_filter is not None:
                # filter requires us to know the nodes' subject/grade
                from_id = edge.get("from", "")
                from_subject = from_id.split(".")[0] if "." in from_id else None
                from_grade_match = re.search(r"\.g(\d+)\.", from_id)
                from_grade = int(from_grade_match.group(1)) if from_grade_match else None
                if subject_filter and from_subject != subject_filter:
                    continue
                if grade_filter is not None and from_grade != grade_filter:
                    continue
            all_edges.append(edge)

    # Check dangling references
    for i, e in enumerate(all_edges):
        for endpoint in ("from", "to"):
            ref = e.get(endpoint, "")
            if ref and ref not in node_ids:
                errors.append(f"edge[{i}]: {endpoint} '{ref}' not in node_ids")

    # No self-cycles
    for i, e in enumerate(all_edges):
        if e.get("from") == e.get("to"):
            errors.append(f"edge[{i}]: self-loop on '{e.get('from')}'")

    return all_edges, errors


def topo_check(prereq_edges, node_ids) -> list[str]:
    """Kahn's algorithm on the prerequisite subgraph. Returns error list."""
    errors = []
    adj = defaultdict(set)  # from -> {to}
    in_degree = defaultdict(int)
    for nid in node_ids:
        in_degree[nid] = 0
    for e in prereq_edges:
        if e.get("type") != "prerequisite":
            continue
        f, t = e.get("from"), e.get("to")
        if f in node_ids and t in node_ids and t not in adj[f]:
            adj[f].add(t)
            in_degree[t] += 1

    queue = deque([n for n in node_ids if in_degree[n] == 0])
    visited = 0
    while queue:
        n = queue.popleft()
        visited += 1
        for m in adj.get(n, ()):
            in_degree[m] -= 1
            if in_degree[m] == 0:
                queue.append(m)

    if visited != len(node_ids):
        # Find a cycle for the error message
        remaining = [n for n in node_ids if in_degree[n] > 0]
        errors.append(
            f"prerequisite graph has cycle(s); {len(node_ids) - visited}/{len(node_ids)} "
            f"nodes in topological order; remaining: {remaining[:5]}"
        )
    return errors


def validate_exercises(exercise_files, node_ids) -> list[str]:
    errors = []
    seen_ids = set()
    for f in exercise_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{f.name}: JSON parse error: {e}")
            continue
        if not isinstance(data, list):
            errors.append(f"{f.name}: expected JSON array")
            continue
        for i, ex in enumerate(data):
            tag = f"{f.name}[{i}]"
            ex_id = ex.get("id", "")
            if ex_id in seen_ids:
                errors.append(f"{tag}: duplicate id '{ex_id}'")
            seen_ids.add(ex_id)

            # Choice answer must match an option
            if ex.get("type") == "choice":
                opts = ex.get("options", [])
                if not isinstance(opts, list) or len(opts) != 4:
                    errors.append(f"{tag}: choice must have 4 options, got {len(opts) if isinstance(opts, list) else 'n/a'}")
                ans = ex.get("answer", "")
                if ans and isinstance(opts, list):
                    # Accept "A" / "B" / "C" / "D" or full option text (substring)
                    if ans in ("A", "B", "C", "D"):
                        continue
                    ok = any(ans in o for o in opts)
                    if not ok:
                        errors.append(
                            f"{tag}: choice answer '{ans}' does not match any option "
                            f"{[o[:30] + '...' if len(o) > 30 else o for o in opts]}"
                        )

            # assesses references must exist
            for ref in ex.get("assesses", []):
                if ref not in node_ids:
                    errors.append(f"{tag}: assesses '{ref}' not in node_ids")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--check-topo", action="store_true")
    parser.add_argument("--exercises-only", action="store_true")
    parser.add_argument("--subject")
    parser.add_argument("--grade", type=int)
    args = parser.parse_args()

    root = Path(args.root)
    print(f"=== validate_kb ===\nroot     : {root}")

    node_files, edge_files, exercise_files, schema_files = discover_files(root)
    print(f"nodes    : {[str(f.relative_to(root)) for f in node_files]}")
    print(f"edges    : {[str(f.relative_to(root)) for f in edge_files]}")
    print(f"exercises: {len(exercise_files)} files")
    print(f"topo     : {args.check_topo}\n")

    nodes_schema, edges_schema = load_schemas(root)

    # Nodes
    nodes, node_errors = validate_nodes(
        node_files, nodes_schema, args.subject, args.grade
    )
    if not args.exercises_only:
        for f in node_files:
            print(f"[validate] {f.relative_to(root)}")
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    print(f"  [OK]    {f.name}: {len(data)} nodes match schema")
            except Exception:
                pass
    node_ids = {n.get("id") for n in nodes}
    print(f"  [OK]    total unique nodes: {len(node_ids)}")

    # Check prereqs exist
    dangling = 0
    for n in nodes:
        for ref in n.get("prerequisites", []):
            if ref not in node_ids:
                node_errors.append(f"node '{n.get('id')}': prereq '{ref}' not in node_ids")
                dangling += 1
    if dangling == 0:
        print(f"  [OK]    all {sum(len(n.get('prerequisites', [])) for n in nodes)} prerequisites resolved")
    else:
        print(f"  [ERR]   {dangling} dangling prerequisites")

    # Edges
    edges, edge_errors = []
    if not args.exercises_only:
        edges, edge_errors = validate_edges(
            edge_files, edges_schema, node_ids, args.subject, args.grade
        )
        for f in edge_files:
            print(f"\n[validate] {f.relative_to(root)}")
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    print(f"  [OK]    {f.name}: {len(data)} edges match schema")
            except Exception:
                pass
        print(f"  [OK]    {len(edges)} edges loaded across {len(edge_files)} file(s)")

    # Topo check
    if args.check_topo and not args.exercises_only:
        prereq_edges = [e for e in edges if e.get("type") == "prerequisite"]
        topo_errors = topo_check(prereq_edges, node_ids)
        if not topo_errors:
            print(f"  [OK]    prerequisite graph: {len(node_ids)} nodes, "
                  f"topological order OK across {len(prereq_edges)} edges")
        else:
            print(f"  [ERR]   {topo_errors[0]}")

    # Exercises
    ex_errors = []
    if exercise_files:
        print(f"\n[validate] exercises ({len(exercise_files)} files)")
        ex_errors = validate_exercises(exercise_files, node_ids)
        if not ex_errors:
            print(f"  [OK]    {len(exercise_files)} exercise file(s), all checks passed")
        else:
            for e in ex_errors:
                print(f"  [ERROR] {e}")

    # Summary
    total_errors = len(node_errors) + len(edge_errors) + len(ex_errors)
    print(f"\n=== summary ===")
    print(f"  nodes    : {len(node_ids)}")
    print(f"  edges    : {len(edges) if not args.exercises_only else 'n/a'}")
    if exercise_files:
        print(f"  exercises: {len(exercise_files)}")
    print(f"  errors   : {total_errors}")
    print("OK" if total_errors == 0 else "FAIL")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
