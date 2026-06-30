from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ..normalize.dates import normalize_date_ym
from ..normalize.location import parse_location
from ..normalize.phones import normalize_phone_e164
from ..normalize.skills import canonicalize_skill
from .base import FieldValue, PartialProfile
from .resume import parse_resume_text
from .notes import parse_recruiter_notes


SOURCE_CONFIDENCE = {
    "recruiter_csv": 0.92,
    "ats_json": 0.88,
    "resume": 0.75,
    "recruiter_notes": 0.55,
    "github_json": 0.70,
}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def ingest_recruiter_csv(path: Path, candidate_id: str | None = None) -> PartialProfile:
    source = "recruiter_csv"
    conf = SOURCE_CONFIDENCE[source]
    profile = PartialProfile(source_name=source)

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    if not rows:
        return profile

    row = rows[0]
    if candidate_id:
        for candidate_row in rows:
            if candidate_row.get("candidate_id", "").strip() == candidate_id:
                row = candidate_row
                break

    cid = (candidate_id or row.get("candidate_id") or row.get("id") or "unknown").strip()
    profile.candidate_id = cid

    profile.add("full_name", row.get("name", "").strip(), "csv_column_map", conf)
    email = row.get("email", "").strip().lower()
    if email:
        profile.add("emails", [email], "csv_column_map", conf)

    phone = normalize_phone_e164(row.get("phone"))
    if phone:
        profile.add("phones", [phone], "phone_e164_normalize", conf * 0.98)

    profile.add("headline", row.get("title", "").strip() or None, "csv_column_map", conf * 0.9)

    company = row.get("current_company", "").strip()
    title = row.get("title", "").strip()
    if company or title:
        profile.experience.append({
            "company": FieldValue(company, source, "csv_column_map", conf),
            "title": FieldValue(title, source, "csv_column_map", conf),
            "start": FieldValue(None, source, "csv_column_map", 0.0),
            "end": FieldValue(None, source, "csv_column_map", 0.0),
            "summary": FieldValue(None, source, "csv_column_map", 0.0),
        })

    location_raw = row.get("location", "").strip()
    if location_raw:
        profile.add("location", parse_location(location_raw), "location_parse", conf * 0.85)

    skills_raw = row.get("skills", "")
    for token in skills_raw.replace(";", ",").split(","):
        skill = canonicalize_skill(token.strip())
        if skill:
            profile.skills.append(FieldValue(skill, source, "skill_canonicalize", conf * 0.8))

    linkedin = row.get("linkedin", "").strip()
    github = row.get("github", "").strip()
    if linkedin or github:
        profile.add("links", {
            "linkedin": linkedin or None,
            "github": github or None,
            "portfolio": None,
            "other": [],
        }, "csv_column_map", conf * 0.95)

    return profile


def ingest_ats_json(path: Path, candidate_id: str | None = None) -> PartialProfile:
    source = "ats_json"
    conf = SOURCE_CONFIDENCE[source]
    profile = PartialProfile(source_name=source)

    data: dict[str, Any] = json.loads(_read_text(path))
    if candidate_id:
        profile.candidate_id = candidate_id
    else:
        profile.candidate_id = str(data.get("applicantId") or data.get("id") or "unknown")

    contact = data.get("contactInfo") or data.get("contact") or {}
    name = data.get("displayName") or data.get("fullName") or contact.get("name")
    profile.add("full_name", name, "ats_field_map", conf)

    email = contact.get("emailAddress") or contact.get("email")
    if email:
        profile.add("emails", [str(email).lower()], "ats_field_map", conf)

    phone_raw = contact.get("mobile") or contact.get("phone")
    phone = normalize_phone_e164(str(phone_raw) if phone_raw else None)
    if phone:
        profile.add("phones", [phone], "phone_e164_normalize", conf * 0.95)

    headline = data.get("professionalSummary") or data.get("headline")
    profile.add("headline", headline, "ats_field_map", conf * 0.85)

    loc = data.get("location") or {}
    if isinstance(loc, dict):
        profile.add("location", {
            "city": loc.get("city"),
            "region": loc.get("state") or loc.get("region"),
            "country": (loc.get("countryCode") or loc.get("country") or "")[:2].upper() or None,
        }, "ats_field_map", conf * 0.9)
    elif isinstance(loc, str):
        profile.add("location", parse_location(loc), "location_parse", conf * 0.8)

    for job in data.get("workHistory") or data.get("experience") or []:
        profile.experience.append({
            "company": FieldValue(job.get("employer") or job.get("company"), source, "ats_field_map", conf),
            "title": FieldValue(job.get("role") or job.get("title"), source, "ats_field_map", conf),
            "start": FieldValue(normalize_date_ym(str(job.get("startDate") or job.get("start") or "")), source, "date_normalize", conf * 0.9),
            "end": FieldValue(normalize_date_ym(str(job.get("endDate") or job.get("end") or "present")), source, "date_normalize", conf * 0.9),
            "summary": FieldValue(job.get("description") or job.get("summary"), source, "ats_field_map", conf * 0.7),
        })

    for edu in data.get("educationHistory") or data.get("education") or []:
        profile.education.append({
            "institution": FieldValue(edu.get("school") or edu.get("institution"), source, "ats_field_map", conf),
            "degree": FieldValue(edu.get("degree"), source, "ats_field_map", conf),
            "field": FieldValue(edu.get("major") or edu.get("field"), source, "ats_field_map", conf),
            "end_year": FieldValue(edu.get("graduationYear") or edu.get("end_year"), source, "ats_field_map", conf * 0.9),
        })

    for skill in data.get("skillTags") or data.get("skills") or []:
        name = skill if isinstance(skill, str) else skill.get("name")
        canonical = canonicalize_skill(str(name) if name else None)
        if canonical:
            profile.skills.append(FieldValue(canonical, source, "skill_canonicalize", conf * 0.85))

    social = data.get("socialProfiles") or {}
    links = {
        "linkedin": social.get("linkedIn") or social.get("linkedin"),
        "github": social.get("github"),
        "portfolio": social.get("portfolio") or social.get("website"),
        "other": [],
    }
    if any(links[k] for k in ("linkedin", "github", "portfolio")):
        profile.add("links", links, "ats_field_map", conf * 0.95)

    years = data.get("totalYearsExperience") or data.get("years_experience")
    if years is not None:
        try:
            profile.add("years_experience", float(years), "ats_field_map", conf * 0.8)
        except (TypeError, ValueError):
            pass

    return profile


def ingest_resume(path: Path, candidate_id: str | None = None) -> PartialProfile:
    source = "resume"
    conf = SOURCE_CONFIDENCE[source]
    profile = PartialProfile(source_name=source, candidate_id=candidate_id or "unknown")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        from docx import Document
        doc = Document(str(path))
        text = "\n".join(p.text for p in doc.paragraphs)
    else:
        text = _read_text(path)

    parsed = parse_resume_text(text)
    profile.add("full_name", parsed.get("full_name"), "resume_regex_extract", conf * 0.7)
    if parsed.get("emails"):
        profile.add("emails", parsed["emails"], "resume_regex_extract", conf * 0.65)
    if parsed.get("phones"):
        profile.add("phones", parsed["phones"], "phone_e164_normalize", conf * 0.6)
    profile.add("headline", parsed.get("headline"), "resume_section_parse", conf * 0.55)
    profile.add("location", parsed.get("location"), "location_parse", conf * 0.5)
    profile.add("years_experience", parsed.get("years_experience"), "resume_heuristic", conf * 0.45)

    for skill in parsed.get("skills", []):
        profile.skills.append(FieldValue(skill, source, "skill_canonicalize", conf * 0.6))

    for exp in parsed.get("experience", []):
        profile.experience.append({
            "company": FieldValue(exp.get("company"), source, "resume_section_parse", conf * 0.55),
            "title": FieldValue(exp.get("title"), source, "resume_section_parse", conf * 0.55),
            "start": FieldValue(exp.get("start"), source, "date_normalize", conf * 0.5),
            "end": FieldValue(exp.get("end"), source, "date_normalize", conf * 0.5),
            "summary": FieldValue(exp.get("summary"), source, "resume_section_parse", conf * 0.45),
        })

    for edu in parsed.get("education", []):
        profile.education.append({
            "institution": FieldValue(edu.get("institution"), source, "resume_section_parse", conf * 0.55),
            "degree": FieldValue(edu.get("degree"), source, "resume_section_parse", conf * 0.55),
            "field": FieldValue(edu.get("field"), source, "resume_section_parse", conf * 0.5),
            "end_year": FieldValue(edu.get("end_year"), source, "resume_section_parse", conf * 0.5),
        })

    if parsed.get("github"):
        profile.add("links", {
            "linkedin": parsed.get("linkedin"),
            "github": parsed.get("github"),
            "portfolio": parsed.get("portfolio"),
            "other": [],
        }, "resume_url_extract", conf * 0.7)

    return profile


def ingest_recruiter_notes(path: Path, candidate_id: str | None = None) -> PartialProfile:
    source = "recruiter_notes"
    conf = SOURCE_CONFIDENCE[source]
    profile = PartialProfile(source_name=source, candidate_id=candidate_id or "unknown")
    parsed = parse_recruiter_notes(_read_text(path))

    profile.add("full_name", parsed.get("full_name"), "notes_regex_extract", conf * 0.5)
    if parsed.get("emails"):
        profile.add("emails", parsed["emails"], "notes_regex_extract", conf * 0.45)
    profile.add("headline", parsed.get("headline"), "notes_heuristic", conf * 0.4)
    profile.add("years_experience", parsed.get("years_experience"), "notes_heuristic", conf * 0.35)

    for skill in parsed.get("skills", []):
        profile.skills.append(FieldValue(skill, source, "skill_canonicalize", conf * 0.4))

    return profile


def ingest_github_json(path: Path, candidate_id: str | None = None) -> PartialProfile:
    """Offline GitHub API response (structured export)."""
    source = "github_json"
    conf = SOURCE_CONFIDENCE[source]
    profile = PartialProfile(source_name=source, candidate_id=candidate_id or "unknown")
    data = json.loads(_read_text(path))

    profile.add("full_name", data.get("name") or data.get("login"), "github_api_map", conf * 0.8)
    profile.add("headline", data.get("bio"), "github_api_map", conf * 0.65)
    profile.add("location", parse_location(data.get("location")), "location_parse", conf * 0.6)

    if data.get("html_url"):
        profile.add("links", {
            "linkedin": None,
            "github": data["html_url"],
            "portfolio": data.get("blog") or None,
            "other": [],
        }, "github_api_map", conf * 0.95)

    for lang in (data.get("top_languages") or data.get("languages") or [])[:10]:
        skill = canonicalize_skill(str(lang))
        if skill:
            profile.skills.append(FieldValue(skill, source, "skill_canonicalize", conf * 0.7))

    return profile


def detect_and_ingest(path: Path, candidate_id: str | None = None) -> PartialProfile:
    suffix = path.suffix.lower()
    name = path.name.lower()

    if suffix == ".csv":
        return ingest_recruiter_csv(path, candidate_id)
    if suffix == ".json" and "github" in name:
        return ingest_github_json(path, candidate_id)
    if suffix == ".json":
        return ingest_ats_json(path, candidate_id)
    if suffix in {".pdf", ".docx", ".txt"} and "note" in name:
        return ingest_recruiter_notes(path, candidate_id)
    if suffix in {".pdf", ".docx", ".txt", ".resume"}:
        return ingest_resume(path, candidate_id)
    if suffix == ".txt":
        return ingest_recruiter_notes(path, candidate_id)

    raise ValueError(f"Unsupported source file: {path}")
