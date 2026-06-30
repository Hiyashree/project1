from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .ingest.sources import detect_and_ingest
from .merge.merger import merge_partials
from .models.config import OutputConfig
from .project.projector import project, validate_output


def run_pipeline(
    source_paths: list[Path],
    candidate_id: str | None,
    config: OutputConfig,
) -> dict:
    partials = []
    for path in source_paths:
        try:
            partials.append(detect_and_ingest(path, candidate_id))
        except Exception as exc:
            # Degrade gracefully — skip bad sources, never crash whole pipeline
            partials.append(_empty_partial(str(path), str(exc)))

    if not any(p.fields or p.skills or p.experience for p in partials):
        raise ValueError("All sources failed to produce usable data")

    canonical = merge_partials([p for p in partials if p.source_name != "failed"])
    canonical_dict = canonical.to_dict()

    projected = project(canonical_dict, config)
    errors = validate_output(projected, config)
    if errors:
        projected["_validation_errors"] = errors

    return projected


def _empty_partial(source_label: str, reason: str):
    from .ingest.base import PartialProfile
    p = PartialProfile(source_name="failed", candidate_id="unknown")
    return p


def load_config(path: Path | None) -> OutputConfig:
    if path is None:
        return OutputConfig.default_canonical()
    data = json.loads(path.read_text(encoding="utf-8"))
    return OutputConfig.from_dict(data)
