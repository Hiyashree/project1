# Technical Design

**Project:** Multi-Source Candidate Data Transformer  
**Author:** HIYASHREE SARMA | hiyasarma90@gmail.com

---

## Pipeline Flow

1. **Detect & Ingest** — Auto-detect source type (CSV, ATS JSON, resume, notes) and parse into `PartialProfile` records with per-field confidence.
2. **Extract** — Map source-specific field names to canonical concepts (e.g., `contactInfo.emailAddress` → `emails`).
3. **Normalize** — E.164 phones, YYYY-MM dates, ISO-3166 countries, canonical skill aliases.
4. **Merge** — Combine partials using confidence-weighted conflict resolution; union lists with deduplication.
5. **Score** — Compute per-skill and overall confidence from source reliability tiers.
6. **Project** — Apply runtime config to reshape canonical record (field select, rename, normalize).
7. **Validate** — Type-check projected output against config; never emit fabricated values.

## Canonical Schema & Formats

| Field | Normalized format |
|-------|-------------------|
| phones | E.164 (`+14155550198`) |
| experience dates | YYYY-MM |
| location.country | ISO-3166 alpha-2 |
| skills | Canonical names (e.g., `k8s` → `Kubernetes`) |

## Merge & Conflict Policy

- **Scalars** (name, headline): highest-confidence source wins.
- **Lists** (emails, phones, skills): union + dedupe, ordered by confidence.
- **Experience/education**: merge all entries, dedupe by company/institution.
- **Principle**: prefer structured sources (CSV 0.92, ATS 0.88) over unstructured (resume 0.75, notes 0.55).

## Custom Output Config

Internal `CanonicalProfile` is never mutated by config. A projection layer maps paths (`from: emails[0]` → `primary_email`), applies per-field normalization, and handles missing values (`null` / `omit` / `error`).

## Edge Cases

| Case | Handling |
|------|----------|
| Invalid phone | Rejected → null (not guessed) |
| Corrupt source file | Skipped; pipeline continues |
| Conflicting emails | Both kept, deduped |
| Missing required field | Config-driven: null/omit/error |
| `"present"` end date | Normalized to current YYYY-MM |

## Descoped

Live GitHub/LinkedIn APIs, batch entity resolution, ML resume parsing, web UI.
