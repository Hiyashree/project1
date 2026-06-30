from __future__ import annotations

from typing import Any

from ..models.canonical import CanonicalProfile, ProvenanceEntry, SkillEntry
from ..normalize.phones import normalize_phones
from ..normalize.location import normalize_country
from ..ingest.base import FieldValue, PartialProfile


def _pick_scalar(values: list[FieldValue]) -> FieldValue | None:
    if not values:
        return None
    return max(values, key=lambda v: v.confidence)


def _merge_lists(values: list[FieldValue], key_fn=None) -> list[Any]:
    seen: set[str] = set()
    ranked: list[tuple[float, Any]] = []
    for fv in sorted(values, key=lambda v: v.confidence, reverse=True):
        items = fv.value if isinstance(fv.value, list) else [fv.value]
        for item in items:
            if item is None:
                continue
            dedupe_key = key_fn(item) if key_fn else str(item).lower()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            ranked.append((fv.confidence, item))
    return [item for _, item in ranked]


def _unwrap_exp_entry(entry: dict) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in entry.items():
        if isinstance(val, FieldValue):
            out[key] = val.value
        else:
            out[key] = val
    return out


def _dedupe_experience(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for entry in entries:
        key = f"{(entry.get('company') or '').lower()}|{(entry.get('title') or '').lower()}"
        if key in seen or key == "|":
            continue
        seen.add(key)
        result.append(entry)
    return result


def _dedupe_education(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for entry in entries:
        key = (entry.get("institution") or "").lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return result


def merge_partials(partials: list[PartialProfile]) -> CanonicalProfile:
    if not partials:
        raise ValueError("No source profiles to merge")

    candidate_ids = [p.candidate_id for p in partials if p.candidate_id]
    candidate_id = candidate_ids[0] if candidate_ids else "unknown"
    profile = CanonicalProfile.empty(candidate_id)

    # Scalar fields
    for field_name in ("full_name", "headline", "years_experience"):
        candidates = [p.fields[field_name] for p in partials if field_name in p.fields]
        winner = _pick_scalar(candidates)
        if winner:
            setattr(profile, field_name, winner.value)
            profile.provenance.append(
                ProvenanceEntry(field=field_name, source=winner.source, method=winner.method)
            )

    # Emails & phones
    email_values = [p.fields["emails"] for p in partials if "emails" in p.fields]
    if email_values:
        merged_emails = _merge_lists(email_values, key_fn=lambda e: e.lower())
        profile.emails = merged_emails
        best = max(email_values, key=lambda v: v.confidence)
        profile.provenance.append(
            ProvenanceEntry(field="emails", source=best.source, method=best.method)
        )

    phone_values = [p.fields["phones"] for p in partials if "phones" in p.fields]
    if phone_values:
        raw_phones: list[str] = []
        for fv in phone_values:
            raw_phones.extend(fv.value if isinstance(fv.value, list) else [fv.value])
        profile.phones = normalize_phones(raw_phones)
        best = max(phone_values, key=lambda v: v.confidence)
        profile.provenance.append(
            ProvenanceEntry(field="phones", source=best.source, method=best.method)
        )

    # Location — field-level merge
    loc_values = [p.fields["location"] for p in partials if "location" in p.fields]
    if loc_values:
        winner = _pick_scalar(loc_values)
        loc = winner.value if winner else {"city": None, "region": None, "country": None}
        if loc.get("country"):
            loc["country"] = normalize_country(loc["country"]) or loc["country"]
        profile.location = loc
        if winner:
            profile.provenance.append(
                ProvenanceEntry(field="location", source=winner.source, method=winner.method)
            )

    # Links
    link_values = [p.fields["links"] for p in partials if "links" in p.fields]
    if link_values:
        merged = {"linkedin": None, "github": None, "portfolio": None, "other": []}
        for fv in sorted(link_values, key=lambda v: v.confidence, reverse=True):
            val = fv.value or {}
            for key in ("linkedin", "github", "portfolio"):
                if not merged[key] and val.get(key):
                    merged[key] = val[key]
            merged["other"].extend(val.get("other") or [])
        profile.links = merged
        best = max(link_values, key=lambda v: v.confidence)
        profile.provenance.append(
            ProvenanceEntry(field="links", source=best.source, method=best.method)
        )

    # Skills — merge by canonical name, keep max confidence & all sources
    skill_map: dict[str, SkillEntry] = {}
    for partial in partials:
        for fv in partial.skills:
            name = fv.value
            if name not in skill_map:
                skill_map[name] = SkillEntry(name=name, confidence=fv.confidence, sources=[fv.source])
            else:
                entry = skill_map[name]
                entry.confidence = max(entry.confidence, fv.confidence)
                if fv.source not in entry.sources:
                    entry.sources.append(fv.source)
    profile.skills = sorted(skill_map.values(), key=lambda s: (-s.confidence, s.name))
    if profile.skills:
        profile.provenance.append(
            ProvenanceEntry(field="skills", source="multi", method="skill_merge_dedupe")
        )

    # Experience & education — collect all, dedupe, prefer higher-confidence duplicates
    all_exp: list[dict[str, Any]] = []
    for partial in partials:
        for entry in partial.experience:
            all_exp.append(_unwrap_exp_entry(entry))
    profile.experience = _dedupe_experience(all_exp)
    if profile.experience:
        profile.provenance.append(
            ProvenanceEntry(field="experience", source="multi", method="experience_merge_dedupe")
        )

    all_edu: list[dict[str, Any]] = []
    for partial in partials:
        for entry in partial.education:
            all_edu.append(_unwrap_exp_entry(entry))
    profile.education = _dedupe_education(all_edu)
    if profile.education:
        profile.provenance.append(
            ProvenanceEntry(field="education", source="multi", method="education_merge_dedupe")
        )

    profile.overall_confidence = _compute_overall_confidence(profile)
    return profile


def _compute_overall_confidence(profile: CanonicalProfile) -> float:
    scores: list[float] = []
    if profile.full_name:
        scores.append(0.9)
    if profile.emails:
        scores.append(0.85)
    if profile.phones:
        scores.append(0.8)
    if profile.experience:
        scores.append(0.75)
    if profile.skills:
        avg_skill = sum(s.confidence for s in profile.skills) / len(profile.skills)
        scores.append(min(avg_skill, 0.85))
    if profile.education:
        scores.append(0.7)
    if profile.headline:
        scores.append(0.65)
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 3)
