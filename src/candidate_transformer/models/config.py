from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


OnMissing = Literal["null", "omit", "error"]


@dataclass
class FieldSpec:
    path: str
    type: str
    from_path: str | None = None
    required: bool = False
    normalize: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FieldSpec:
        return cls(
            path=data["path"],
            type=data["type"],
            from_path=data.get("from"),
            required=data.get("required", False),
            normalize=data.get("normalize"),
        )


@dataclass
class OutputConfig:
    fields: list[FieldSpec]
    include_confidence: bool = False
    include_provenance: bool = False
    on_missing: OnMissing = "null"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OutputConfig:
        return cls(
            fields=[FieldSpec.from_dict(f) for f in data.get("fields", [])],
            include_confidence=data.get("include_confidence", False),
            include_provenance=data.get("include_provenance", False),
            on_missing=data.get("on_missing", "null"),
        )

    @classmethod
    def default_canonical(cls) -> OutputConfig:
        """Full canonical schema projection."""
        return cls(
            fields=[
                FieldSpec("candidate_id", "string"),
                FieldSpec("full_name", "string"),
                FieldSpec("emails", "string[]"),
                FieldSpec("phones", "string[]"),
                FieldSpec("location", "object"),
                FieldSpec("links", "object"),
                FieldSpec("headline", "string"),
                FieldSpec("years_experience", "number"),
                FieldSpec("skills", "object[]"),
                FieldSpec("experience", "object[]"),
                FieldSpec("education", "object[]"),
                FieldSpec("provenance", "object[]"),
                FieldSpec("overall_confidence", "number"),
            ],
            include_confidence=True,
            include_provenance=True,
            on_missing="null",
        )
