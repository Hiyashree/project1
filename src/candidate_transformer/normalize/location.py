from __future__ import annotations

import re

_COUNTRY_ALIASES: dict[str, str] = {
    "usa": "US",
    "us": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "united states": "US",
    "united states of america": "US",
    "uk": "GB",
    "u.k.": "GB",
    "united kingdom": "GB",
    "great britain": "GB",
    "england": "GB",
    "canada": "CA",
    "india": "IN",
    "germany": "DE",
    "france": "FR",
    "australia": "AU",
    "japan": "JP",
    "singapore": "SG",
}


def normalize_country(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip()
    if re.fullmatch(r"[A-Za-z]{2}", text):
        return text.upper()
    key = text.lower()
    return _COUNTRY_ALIASES.get(key)


def parse_location(raw: str | None) -> dict[str, str | None]:
    """Parse 'City, Region, Country' style strings."""
    empty = {"city": None, "region": None, "country": None}
    if not raw or not str(raw).strip():
        return empty

    parts = [p.strip() for p in str(raw).split(",") if p.strip()]
    if not parts:
        return empty

    if len(parts) == 1:
        country = normalize_country(parts[0])
        if country:
            return {"city": None, "region": None, "country": country}
        return {"city": parts[0], "region": None, "country": None}

    if len(parts) == 2:
        country = normalize_country(parts[1])
        return {"city": parts[0], "region": None, "country": country}

    country = normalize_country(parts[-1])
    region = parts[-2]
    city = ", ".join(parts[:-2])
    return {"city": city or None, "region": region or None, "country": country}
