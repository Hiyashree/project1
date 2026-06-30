from __future__ import annotations

import re

# Common skill aliases → canonical name
_SKILL_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python3": "Python",
    "python": "Python",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "reactjs": "React",
    "react.js": "React",
    "react": "React",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "psql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "aws": "Amazon Web Services",
    "gcp": "Google Cloud Platform",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
    "go lang": "Go",
    "golang": "Go",
    "go": "Go",
    "java": "Java",
    "sql": "SQL",
    "html": "HTML",
    "css": "CSS",
    "docker": "Docker",
    "git": "Git",
    "linux": "Linux",
    "rest": "REST APIs",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
}


def canonicalize_skill(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    cleaned = re.sub(r"[^\w\s+#.+/-]", "", str(raw).strip())
    key = cleaned.lower().strip()
    if not key:
        return None
    if key in _SKILL_ALIASES:
        return _SKILL_ALIASES[key]
    # Title-case unknown skills but preserve known acronyms
    if key.upper() in {"SQL", "HTML", "CSS", "AWS", "GCP", "API"}:
        return key.upper()
    if "+" in cleaned:
        return cleaned  # C++, C#
    return cleaned.title()


def canonicalize_skills(raw_skills: list[str] | None) -> list[str]:
    if not raw_skills:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for skill in raw_skills:
        canonical = canonicalize_skill(skill)
        if canonical and canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result
