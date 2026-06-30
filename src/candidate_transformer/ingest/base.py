from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models.canonical import ProvenanceEntry


@dataclass
class FieldValue:
    value: Any
    source: str
    method: str
    confidence: float


@dataclass
class PartialProfile:
    """Intermediate record from a single source before merge."""
    candidate_id: str | None = None
    source_name: str = "unknown"
    fields: dict[str, FieldValue] = field(default_factory=dict)
    skills: list[FieldValue] = field(default_factory=list)
    experience: list[dict[str, FieldValue | Any]] = field(default_factory=list)
    education: list[dict[str, FieldValue | Any]] = field(default_factory=list)

    def add(self, field_name: str, value: Any, method: str, confidence: float) -> None:
        if value is None:
            return
        if isinstance(value, str) and not value.strip():
            return
        if isinstance(value, (list, dict)) and not value:
            return
        self.fields[field_name] = FieldValue(
            value=value,
            source=self.source_name,
            method=method,
            confidence=confidence,
        )

    def provenance_for(self, field_name: str) -> ProvenanceEntry | None:
        fv = self.fields.get(field_name)
        if not fv:
            return None
        return ProvenanceEntry(field=field_name, source=fv.source, method=fv.method)
