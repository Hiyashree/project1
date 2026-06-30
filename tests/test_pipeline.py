"""Tests for the candidate transformer pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from candidate_transformer.models.config import OutputConfig
from candidate_transformer.normalize.dates import normalize_date_ym
from candidate_transformer.normalize.phones import normalize_phone_e164
from candidate_transformer.normalize.skills import canonicalize_skill
from candidate_transformer.pipeline import load_config, run_pipeline
from candidate_transformer.project.projector import project, validate_output


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample"


class TestNormalization:
    def test_phone_e164_us(self):
        assert normalize_phone_e164("(415) 555-0198") == "+14155550198"

    def test_phone_garbage_returns_none(self):
        assert normalize_phone_e164("not-a-phone") is None

    def test_date_formats(self):
        assert normalize_date_ym("2021-03") == "2021-03"
        assert normalize_date_ym("03-2021") == "2021-03"
        assert normalize_date_ym("Mar 2021") == "2021-03"
        assert normalize_date_ym("present") is not None

    def test_skill_aliases(self):
        assert canonicalize_skill("py") == "Python"
        assert canonicalize_skill("k8s") == "Kubernetes"
        assert canonicalize_skill("javascript") == "JavaScript"


class TestProjector:
    def test_custom_field_mapping(self):
        canonical = {
            "full_name": "Alex Rivera",
            "emails": ["alex@example.com"],
            "phones": ["+14155550198"],
            "skills": [{"name": "Python", "confidence": 0.9, "sources": ["csv"]}],
            "overall_confidence": 0.85,
            "provenance": [],
        }
        config = OutputConfig.from_dict(json.loads((ROOT / "configs" / "hr_view.json").read_text()))
        out = project(canonical, config)
        assert out["primary_email"] == "alex@example.com"
        assert out["phone"] == "+14155550198"
        assert "Python" in out["skills"]
        assert out["_confidence"] == 0.85
        assert validate_output(out, config) == []


class TestPipeline:
    def test_end_to_end_default_schema(self):
        config = OutputConfig.default_canonical()
        result = run_pipeline(
            [
                SAMPLE / "candidates.csv",
                SAMPLE / "ats_profile.json",
                SAMPLE / "resume.txt",
                SAMPLE / "recruiter_notes.txt",
            ],
            candidate_id="CAND-001",
            config=config,
        )
        assert result["full_name"] == "Alex Rivera"
        assert result["candidate_id"] == "CAND-001"
        assert result["emails"]
        assert result["phones"][0].startswith("+")
        assert result["overall_confidence"] > 0
        assert result["provenance"]

    def test_graceful_missing_source(self, tmp_path: Path):
        config = OutputConfig.default_canonical()
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        result = run_pipeline([SAMPLE / "candidates.csv", bad], None, config)
        assert result["full_name"]

    def test_gold_profile_snapshot(self):
        """Regression: key fields stable for sample Alex Rivera."""
        config = OutputConfig.default_canonical()
        result = run_pipeline(
            [SAMPLE / "candidates.csv", SAMPLE / "ats_profile.json", SAMPLE / "resume.txt"],
            "CAND-001",
            config,
        )
        assert result["full_name"] == "Alex Rivera"
        assert "+14155550198" in result["phones"]
        skill_names = {s["name"] for s in result["skills"]}
        assert "Python" in skill_names
        assert "PostgreSQL" in skill_names
        assert result["experience"][0]["company"] == "Stripe"
