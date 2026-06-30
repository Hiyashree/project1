from __future__ import annotations

import re
from typing import Any

from ..normalize.dates import normalize_date_ym, parse_year_from_text
from ..normalize.location import parse_location
from ..normalize.phones import normalize_phone_e164
from ..normalize.skills import canonicalize_skills


_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
_URL_RE = re.compile(r"https?://[^\s]+|(?:github\.com|linkedin\.com)/[^\s]+", re.I)
_YEARS_EXP_RE = re.compile(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?experience", re.I)


def parse_resume_text(text: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    result: dict[str, Any] = {
        "full_name": None,
        "emails": [],
        "phones": [],
        "headline": None,
        "location": None,
        "years_experience": None,
        "skills": [],
        "experience": [],
        "education": [],
        "linkedin": None,
        "github": None,
        "portfolio": None,
    }

    if lines:
        # First non-contact line is often the name
        candidate_name = lines[0]
        if "@" not in candidate_name and not _PHONE_RE.search(candidate_name):
            result["full_name"] = candidate_name

    emails = sorted(set(m.lower() for m in _EMAIL_RE.findall(text)))
    result["emails"] = emails[:3]

    phones: list[str] = []
    for match in _PHONE_RE.findall(text):
        normalized = normalize_phone_e164(match)
        if normalized and normalized not in phones:
            phones.append(normalized)
    result["phones"] = phones[:2]

    for url in _URL_RE.findall(text):
        lower = url.lower()
        if "linkedin.com" in lower and not result["linkedin"]:
            result["linkedin"] = url if url.startswith("http") else f"https://{url}"
        elif "github.com" in lower and not result["github"]:
            result["github"] = url if url.startswith("http") else f"https://{url}"
        elif not result["portfolio"] and "github" not in lower and "linkedin" not in lower:
            result["portfolio"] = url if url.startswith("http") else f"https://{url}"

    exp_match = _YEARS_EXP_RE.search(text)
    if exp_match:
        result["years_experience"] = float(exp_match.group(1))

    lower_text = text.lower()
    for section_key, aliases in {
        "skills": ("skills", "technical skills", "technologies"),
        "experience": ("experience", "work experience", "employment"),
        "education": ("education", "academic"),
    }.items():
        for alias in aliases:
            idx = lower_text.find(alias)
            if idx >= 0:
                chunk = text[idx: idx + 800]
                if section_key == "skills":
                    result["skills"] = _parse_skills_section(chunk)
                elif section_key == "experience":
                    result["experience"] = _parse_experience_section(chunk)
                elif section_key == "education":
                    result["education"] = _parse_education_section(chunk)
                break

    # Headline: line after name if short
    if len(lines) > 1 and len(lines[1]) < 80 and "@" not in lines[1]:
        result["headline"] = lines[1]

    # Location heuristic
    for line in lines[:6]:
        if "," in line and "@" not in line and len(line) < 60:
            loc = parse_location(line)
            if loc.get("city") or loc.get("country"):
                result["location"] = loc
                break

    return result


def _parse_skills_section(chunk: str) -> list[str]:
    lines = chunk.splitlines()[1:6]
    tokens: list[str] = []
    for line in lines:
        tokens.extend(re.split(r"[,|•·\|]", line))
    return canonicalize_skills([t.strip() for t in tokens if t.strip()])


def _parse_experience_section(chunk: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    blocks = re.split(r"\n\s*\n", chunk)
    for block in blocks[1:3]:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        date_match = re.search(
            r"(\w+\s+\d{4}|\d{4}-\d{2})\s*[-–]\s*(\w+\s+\d{4}|\d{4}-\d{2}|present|current)",
            block,
            re.I,
        )
        start = normalize_date_ym(date_match.group(1)) if date_match else None
        end = normalize_date_ym(date_match.group(2)) if date_match else None
        entries.append({
            "company": lines[0] if lines else None,
            "title": lines[1] if len(lines) > 1 else None,
            "start": start,
            "end": end,
            "summary": " ".join(lines[2:])[:200] if len(lines) > 2 else None,
        })
    return entries


def _parse_education_section(chunk: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", chunk)[1:3]:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        year = parse_year_from_text(block)
        degree = None
        field = None
        for line in lines:
            if re.search(r"\b(b\.?s\.?|m\.?s\.?|b\.?a\.?|ph\.?d\.?|bachelor|master)\b", line, re.I):
                degree = line
                break
        if len(lines) > 1 and degree != lines[1]:
            field = lines[1]
        entries.append({
            "institution": lines[0],
            "degree": degree,
            "field": field,
            "end_year": year,
        })
    return entries
