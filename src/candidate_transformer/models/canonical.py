from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ProvenanceEntry:
    field: str
    source: str
    method: str


@dataclass
class SkillEntry:
    name: str
    confidence: float
    sources: list[str] = field(default_factory=list)


@dataclass
class CanonicalProfile:
    candidate_id: str | None = None
    full_name: str | None = None
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    location: dict[str, str | None] | None = None
    links: dict[str, Any] | None = None
    headline: str | None = None
    years_experience: float | None = None
    skills: list[SkillEntry] = field(default_factory=list)
    experience: list[dict[str, Any]] = field(default_factory=list)
    education: list[dict[str, Any]] = field(default_factory=list)
    provenance: list[ProvenanceEntry] = field(default_factory=list)
    overall_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["skills"] = [asdict(s) for s in self.skills]
        data["provenance"] = [asdict(p) for p in self.provenance]
        return data

    @classmethod
    def empty(cls, candidate_id: str) -> CanonicalProfile:
        return cls(
            candidate_id=candidate_id,
            location={"city": None, "region": None, "country": None},
            links={"linkedin": None, "github": None, "portfolio": None, "other": []},
        )
