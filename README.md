# Multi-Source Candidate Data Transformer

**Author:** HIYASHREE SARMA · hiyasarma90@gmail.com

A Python CLI pipeline that ingests messy candidate data from **multiple sources**, normalizes and merges it into a single **canonical profile**, then **projects** that profile to any output schema via runtime configuration.

---

## Architecture

```
Sources (CSV, ATS JSON, Resume, Notes, GitHub JSON)
        │
        ▼
   Ingest & Extract ──► PartialProfile per source
        │
        ▼
   Normalize (E.164 phones, YYYY-MM dates, canonical skills)
        │
        ▼
   Merge & Dedupe ──► CanonicalProfile (internal truth)
        │
        ▼
   Project & Validate ──► Output JSON (config-driven)
```

**Design principle:** Wrong-but-confident is worse than honestly empty. The engine never fabricates data — unknown or garbage values become `null` or are omitted.

---

## Repository Layout

```
Project/
├── src/candidate_transformer/   # Core engine
│   ├── ingest/                  # Source parsers (CSV, ATS, resume, notes)
│   ├── normalize/               # Phone, date, skill, location normalization
│   ├── merge/                   # Multi-source merge & conflict resolution
│   ├── project/                 # Config-driven output projection
│   ├── pipeline.py              # Orchestration
│   └── cli.py                   # Command-line interface
├── data/sample/                 # Sample input files
├── configs/                     # Output projection configs
├── output/                      # Pre-generated sample outputs
├── tests/                       # pytest suite
├── requirements.txt
├── pyproject.toml
├── README.md
└── ASSUMPTIONS.md
```

---

## Quick Start

### 1. Setup

```bash
cd Project
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

### 2. Run — Default Canonical Output

```bash
python -m candidate_transformer \
  data/sample/candidates.csv \
  data/sample/ats_profile.json \
  data/sample/resume.txt \
  data/sample/recruiter_notes.txt \
  --candidate-id CAND-001 \
  -o output/canonical_profile.json
```

### 3. Run — Custom HR View Config

```bash
python -m candidate_transformer \
  data/sample/candidates.csv \
  data/sample/ats_profile.json \
  data/sample/resume.txt \
  -c configs/hr_view.json \
  -o output/hr_view_profile.json
```

---

## Supported Input Sources

| Source | Type | File example |
|--------|------|--------------|
| Recruiter CSV | Structured | `data/sample/candidates.csv` |
| ATS JSON blob | Structured | `data/sample/ats_profile.json` |
| Resume (TXT/PDF/DOCX) | Unstructured | `data/sample/resume.txt` |
| Recruiter notes | Unstructured | `data/sample/recruiter_notes.txt` |
| GitHub profile JSON | Semi-structured | `data/sample/github_profile.json` |

The tool auto-detects source type from file extension and naming.

---

## Merge & Confidence Policy

| Source type | Base confidence | Wins when |
|-------------|-----------------|-----------|
| Recruiter CSV | 0.92 | Structured contact fields |
| ATS JSON | 0.88 | Experience, education, dates |
| Resume | 0.75 | Skills, narrative details |
| GitHub JSON | 0.70 | Links, language skills |
| Recruiter notes | 0.55 | Soft signals only |

**Conflict resolution:** For scalar fields, the value with the **highest source confidence** wins. Lists (emails, phones, skills) are **unioned and deduplicated**. Experience/education entries are deduped by company/institution.

---

## Custom Output Config

See `configs/hr_view.json`:

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

Supported `on_missing` values: `null`, `omit`, `error`.

---

## Running Tests

```bash
pytest -v
```
