# Assumptions & Descoped Features

**Author:** HIYASHREE SARMA · hiyasarma90@gmail.com

## Assumptions

1. **Single candidate per run** — The CLI merges all provided sources into one profile. Batch CSV processing can be added by looping in a wrapper script.
2. **GitHub via offline JSON** — Live GitHub API calls require tokens and rate limits; we accept a saved API response (`github_profile.json`) instead.
3. **No LinkedIn scraping** — LinkedIn blocks automated access; URLs are preserved when found in CSV/resume but not scraped.
4. **US-default phone region** — E.164 normalization defaults to `US` when no country code is present.
5. **Resume parsing is heuristic** — PDF/DOCX text extraction + regex/section parsing; not a full NLP pipeline.
6. **Deterministic** — No LLM calls; same inputs always produce the same output.

## Edge Cases Handled

| Edge case | Behavior |
|-----------|----------|
| Invalid phone number | Returns `null`, excluded from output |
| Corrupt/missing source file | Skipped gracefully; other sources still merge |
| Conflicting emails across sources | Both kept (deduped), ordered by source confidence |
| `"present"` end dates | Normalized to current YYYY-MM |
| Unknown skill names | Title-cased, not dropped |
| Required field missing in custom config | `null` (default), `omit`, or `error` per config |

## Descoped

- Real-time GitHub/LinkedIn API integrations
- Fuzzy candidate matching across batches (entity resolution)
- Web UI
- ML-based resume parsing

## Features Included

- Structured + unstructured source ingestion
- Canonical internal schema with provenance
- Per-field and overall confidence scores
- Runtime output projection config
- Output validation
- CLI + tests + sample outputs
