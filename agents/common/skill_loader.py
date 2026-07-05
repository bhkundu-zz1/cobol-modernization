"""Loads a SKILL.md file and computes its content hash (architecture.md section 3.5).

The agent runtime loads the skill file at task start and records its
content hash into agent_task.skill_version_hash, so every recommendation is
traceable to the exact skill wording that produced it — required for the
audit trail.
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml

_SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"


@dataclass
class Skill:
    name: str
    description: str
    model: str
    version: int
    inputs: list[str]
    outputs: list[str]
    tools_allowed: list[str]
    body: str
    content_hash: str


def _split_frontmatter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        raise ValueError("SKILL.md must start with a YAML frontmatter block delimited by '---'")
    _, frontmatter_raw, body = raw.split("---", 2)
    frontmatter = yaml.safe_load(frontmatter_raw) or {}
    return frontmatter, body.strip()


def load_skill(skill_dir_name: str) -> Skill:
    """skill_dir_name matches the folder name under agents/skills/, e.g.
    'cobol-structural-analysis'."""
    path = _SKILLS_ROOT / skill_dir_name / "SKILL.md"
    raw = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(raw)
    content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    return Skill(
        name=frontmatter["name"],
        description=frontmatter["description"],
        model=frontmatter["model"],
        version=frontmatter.get("version", 1),
        inputs=frontmatter.get("inputs", []),
        outputs=frontmatter.get("outputs", []),
        tools_allowed=frontmatter.get("tools_allowed", []),
        body=body,
        content_hash=content_hash,
    )
