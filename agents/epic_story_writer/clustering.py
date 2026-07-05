"""Deterministic connected-components clustering of COBOL programs into
epic candidates (agents/skills/epic-story-writer/SKILL.md, Step 1).

Programs are connected if they share a copybook (copybooks_referenced
overlap) or have a call_graph edge between them. The graph itself is
computed here, not by an LLM — only the resulting cluster's title/
description is drafted by a model (agents/epic_story_writer/task.py).
"""


def _union(parent: dict[str, str], node: str) -> str:
    while parent[node] != node:
        parent[node] = parent[parent[node]]
        node = parent[node]
    return node


def _connect(parent: dict[str, str], a: str, b: str) -> None:
    root_a, root_b = _union(parent, a), _union(parent, b)
    if root_a != root_b:
        parent[root_a] = root_b


def cluster_programs(structures: list[dict]) -> list[list[str]]:
    """`structures` is a list of cobol_program_structure docs. Returns a
    list of clusters, each a list of `program_id`s, in deterministic order
    (by each cluster's minimum program_id, then programs within a cluster
    sorted) so output is stable across runs for the same input set."""
    program_ids = [s["program_id"] for s in structures]
    parent = {pid: pid for pid in program_ids}

    copybook_owners: dict[str, list[str]] = {}
    for structure in structures:
        for copybook in structure.get("copybooks_referenced", []):
            copybook_owners.setdefault(copybook, []).append(structure["program_id"])

    for owners in copybook_owners.values():
        for other in owners[1:]:
            _connect(parent, owners[0], other)

    program_id_set = set(program_ids)
    for structure in structures:
        source = structure["program_id"]
        for edge in structure.get("call_graph", {}).get("edges", []):
            target = edge.get("to")
            if target in program_id_set:
                _connect(parent, source, target)

    clusters: dict[str, list[str]] = {}
    for pid in program_ids:
        root = _union(parent, pid)
        clusters.setdefault(root, []).append(pid)

    return sorted((sorted(members) for members in clusters.values()), key=lambda members: members[0])
