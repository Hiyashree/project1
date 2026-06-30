from __future__ import annotations

import re
from typing import Any

from ..models.config import FieldSpec, OutputConfig
from ..normalize.phones import normalize_phone_e164
from ..normalize.skills import canonicalize_skill


_ARRAY_INDEX_RE = re.compile(r"^(.+)\[(\d+)\]$")
_ARRAY_WILDCARD_RE = re.compile(r"^(.+)\[\]\.(.+)$")


def project(canonical: dict[str, Any], config: OutputConfig) -> dict[str, Any]:
    output: dict[str, Any] = {}

    for spec in config.fields:
        source_path = spec.from_path or spec.path
        value = _resolve_path(canonical, source_path)

        if spec.normalize == "E164" and isinstance(value, str):
            value = normalize_phone_e164(value)
        elif spec.normalize == "canonical" and isinstance(value, str):
            value = canonicalize_skill(value)
        elif spec.normalize == "canonical" and isinstance(value, list):
            value = [canonicalize_skill(v) for v in value if canonicalize_skill(v)]

        if value is None or value == "" or value == []:
            if spec.required and config.on_missing == "error":
                raise ValueError(f"Required field missing: {spec.path}")
            if config.on_missing == "omit":
                continue
            value = None

        typed = _coerce_type(value, spec.type)
        output[spec.path] = typed

    if config.include_confidence:
        output["_confidence"] = canonical.get("overall_confidence")
    if config.include_provenance:
        output["_provenance"] = canonical.get("provenance")

    return output


def _resolve_path(data: dict[str, Any], path: str) -> Any:
    wildcard = _ARRAY_WILDCARD_RE.match(path)
    if wildcard:
        base_path, sub_path = wildcard.group(1), wildcard.group(2)
        items = _resolve_path(data, base_path)
        if not isinstance(items, list):
            return None
        return [_resolve_path(item, sub_path) if isinstance(item, dict) else item for item in items]

    parts = path.split(".")
    current: Any = data
    for part in parts:
        if current is None:
            return None
        index_match = _ARRAY_INDEX_RE.match(part)
        if index_match:
            key, idx = index_match.group(1), int(index_match.group(2))
            if key:
                current = current.get(key) if isinstance(current, dict) else None
            if not isinstance(current, list) or idx >= len(current):
                return None
            current = current[idx]
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _coerce_type(value: Any, type_name: str) -> Any:
    if value is None:
        return None
    if type_name == "string":
        return str(value)
    if type_name == "number":
        return float(value) if value is not None else None
    if type_name == "string[]":
        if isinstance(value, list):
            return [str(v) for v in value if v is not None]
        return [str(value)]
    if type_name == "object[]":
        return value if isinstance(value, list) else [value]
    if type_name == "object":
        return value if isinstance(value, dict) else None
    return value


def validate_output(output: dict[str, Any], config: OutputConfig) -> list[str]:
    errors: list[str] = []
    for spec in config.fields:
        if spec.path not in output:
            if spec.required and config.on_missing == "error":
                errors.append(f"Missing required field: {spec.path}")
            continue
        value = output[spec.path]
        if spec.required and value is None:
            errors.append(f"Required field is null: {spec.path}")
        if not _type_matches(value, spec.type):
            errors.append(f"Type mismatch for {spec.path}: expected {spec.type}, got {type(value).__name__}")
    return errors


def _type_matches(value: Any, type_name: str) -> bool:
    if value is None:
        return True
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "string[]":
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if type_name == "object[]":
        return isinstance(value, list)
    if type_name == "object":
        return isinstance(value, dict)
    return True
