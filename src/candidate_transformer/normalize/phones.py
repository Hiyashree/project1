from __future__ import annotations

import re

import phonenumbers
from phonenumbers import NumberParseException


def normalize_phone_e164(raw: str | None, default_region: str = "US") -> str | None:
    if not raw or not str(raw).strip():
        return None
    text = re.sub(r"[^\d+]", "", str(raw).strip())
    if not text:
        return None
    try:
        parsed = phonenumbers.parse(text, default_region)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except NumberParseException:
        return None


def normalize_phones(raw_values: list[str] | None, default_region: str = "US") -> list[str]:
    if not raw_values:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for value in raw_values:
        normalized = normalize_phone_e164(value, default_region)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
