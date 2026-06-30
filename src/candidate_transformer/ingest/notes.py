from __future__ import annotations

import re
from typing import Any

from ..normalize.skills import canonicalize_skills


def parse_recruiter_notes(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "full_name": None,
        "emails": [],
        "headline": None,
        "years_experience": None,
        "skills": [],
    }

    # "Candidate: Jane Doe" or "Name - Jane Doe"
    name_match = re.search(r"(?:candidate|name)\s*[:\-]\s*(.+)", text, re.I)
    if name_match:
        result["full_name"] = name_match.group(1).strip().split("\n")[0][:80]

    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    result["emails"] = sorted(set(e.lower() for e in emails))

    headline_match = re.search(r"(?:role|title|position)\s*[:\-]\s*(.+)", text, re.I)
    if headline_match:
        result["headline"] = headline_match.group(1).strip().split("\n")[0][:120]

    years_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*years?", text, re.I)
    if years_match:
        result["years_experience"] = float(years_match.group(1))

    skills_match = re.search(r"skills?\s*[:\-]\s*(.+)", text, re.I)
    if skills_match:
        raw = skills_match.group(1).split("\n")[0]
        result["skills"] = canonicalize_skills(re.split(r"[,;|]", raw))

    # Fallback skill mentions
    if not result["skills"]:
        known = ["python", "java", "react", "aws", "kubernetes", "sql", "machine learning"]
        lower = text.lower()
        result["skills"] = canonicalize_skills([k for k in known if k in lower])

    return result
