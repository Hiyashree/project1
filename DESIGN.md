# Technical Design

**Project:** Multi-Source Candidate Data Transformer  
**Author:** HIYASHREE SARMA | hiyasarma90@gmail.com

---

## Pipeline Flow

1. **Detect & Ingest** — Auto-detect source type (CSV, ATS JSON, resume, notes) → `PartialProfile` per source with per-field confidence.
2. **Extract** — Map source-specific fields to canonical concepts (e.g. `contactInfo.emailAddress` → `emails`).
3. **Normalize** — E.164 phones, YYYY-MM dates, ISO-3166 countries, canonical skill aliases.
4. **Merge** — Confidence-weighted conflict resolution; union lists with deduplication.
5. **Score** — Per-skill and overall confidence from source reliability tiers.
6. **Project** — Runtime config reshapes canonical record (field select, rename, normalize).
7. **Validate** — Type-check projected output against config before return; never fabricate values.

## Canonical Output Schema

| Field | Type | Normalized format |
|-------|------|-------------------|
| candidate_id | string | opaque ID from source or CLI |
| full_name | string | trimmed plain text |
| emails | string[] | lowercase, deduped |
| phones | string[] | E.164 (e.g. `+14155550198`) |
| location | object | `{ city, region, country }` — country ISO-3166 alpha-2 |
| links | object | `{ linkedin, github, portfolio, other[] }` |
| headline | string \| null | trimmed plain text |
| years_experience | number \| null | float, from structured or parsed text |
| skills | object[] | `{ name, confidence, sources[] }` — canonical names (`k8s` → `Kubernetes`) |
| experience | object[] | `{ company, title, start, end, summary }` — dates YYYY-MM |
| education | object[] | `{ institution, degree, field, end_year }` |
| provenance | object[] | `{ field, source, method }` — origin of each merged value |
| overall_confidence | number | 0–1 aggregate score |

## Merge & Conflict Policy

- **Scalars** (name, headline, years_experience): highest-confidence source wins.
- **Lists** (emails, phones, skills): union + dedupe; order by source confidence.
- **Experience / education**: merge all entries; dedupe by company or institution key.
- **Confidence tiers**: recruiter CSV 0.92, ATS JSON 0.88, resume 0.75, GitHub JSON 0.70, recruiter notes 0.55.
- **Principle**: wrong-but-confident is worse than honestly empty — unknown values become `null`.

## Runtime Custom-Output Config

The internal `CanonicalProfile` is never mutated. A **projection layer** reads a JSON config at runtime:

- **Field subset** — `fields[]` lists only the output paths to emit.
- **Rename / remap** — `"from": "emails[0]"` maps a canonical path to `"path": "primary_email"`.
- **Per-field normalize** — `"normalize": "E164"` or `"canonical"` applied during projection.
- **Metadata toggles** — `include_confidence` / `include_provenance` add `_confidence` and `_provenance` blocks.
- **Missing values** — `on_missing`: `null` (default), `omit` (drop field), or `error` (fail validation).
- **Validation** — after projection, each field is type-checked (`string`, `string[]`, `number`, `object`, etc.); required fields enforced per config.

Example (`configs/hr_view.json`):

```json
{
  "fields": [
    { "path": "full_name", "type": "string", "required": true },
    { "path": "primary_email", "from": "emails[0]", "type": "string", "required": true },
    { "path": "phone", "from": "phones[0]", "type": "string", "normalize": "E164" },
    { "path": "skills", "from": "skills[].name", "type": "string[]", "normalize": "canonical" }
  ],
  "include_confidence": true,
  "on_missing": "null"
}
```

## Edge Cases

| Case | Handling |
|------|----------|
| Invalid phone | Rejected → `null`; never guessed |
| Corrupt / unreadable source | Skipped gracefully; other sources still merge |
| Conflicting emails across sources | Both kept, deduped, ordered by confidence |
| Missing required field in config | `null`, omitted, or error per `on_missing` |
| `"present"` / `"current"` end dates | Normalized to current YYYY-MM |

## Descoped (Time Constraints)

Live GitHub/LinkedIn API integrations, batch entity resolution across candidates, ML-based resume parsing, web UI.
