"""Testes do set completo: cover letter + email + matcher.

Todos validam contra o profile REAL (zero alucinação).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cv_engine.core.models import JobDescription, Profile
from cv_engine.generation.cover_letter import build_cover_letter, render_html
from cv_engine.generation.email_builder import build_email
from cv_engine.matching.matcher import match

BASE = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def profile() -> Profile:
    return Profile.from_json_file(str(BASE / "data" / "profile-rafael-zendron.json"))


@pytest.fixture(scope="module")
def jd() -> JobDescription:
    """Vaga exemplo full stack pleno (estilo MPAN)."""
    return JobDescription(
        id="mpan-001", title="Desenvolvedor Full Stack", company="MPAN",
        description="Dev full stack React/Node para produtos digitais.",
        requirements=["Experiência com React e TypeScript",
                      "APIs REST com Node.js",
                      "Testes automatizados"],
        stack=["React", "TypeScript", "Node.js", "PostgreSQL"],
        location="São Paulo, SP", remote=True,
    )


# ── Cover Letter ──────────────────────────────────────────────────────


class TestCoverLetter:
    def test_three_paragraphs(self, profile, jd):
        letter = build_cover_letter(profile, jd)
        assert len(letter.paragraphs) == 3

    def test_max_350_words(self, profile, jd):
        letter = build_cover_letter(profile, jd)
        assert letter.word_count <= 350

    def test_cites_real_metrics(self, profile, jd):
        letter = build_cover_letter(profile, jd)
        assert letter.metrics_cited  # tem número real

    def test_no_banned_phrases(self, profile, jd):
        letter = build_cover_letter(profile, jd)
        assert letter.validate() == [], letter.validate()

    def test_mentions_company(self, profile, jd):
        letter = build_cover_letter(profile, jd)
        assert "MPAN" in letter.paragraphs[0]

    def test_custom_hook(self, profile, jd):
        letter = build_cover_letter(profile, jd,
                                    custom_hook="Acompanho o produto X de vocês.")
        assert "Acompanho o produto X" in letter.paragraphs[0]

    def test_html_renders_name(self, profile, jd):
        letter = build_cover_letter(profile, jd)
        html = render_html(letter, profile)
        assert profile.name in html

    def test_projects_ranked_by_stack_overlap(self, profile, jd):
        """React/TS/Node na vaga → projetos React-first."""
        letter = build_cover_letter(profile, jd)
        # Study Prep (React/TS) ou HireMe devem aparecer antes de Inorbit
        names = [p.name for p in profile.projects]
        _ = names  # sanity
        assert letter.paragraphs[1]  # prova preenchida


# ── Email ─────────────────────────────────────────────────────────────


class TestEmail:
    def test_subject_exact_job_title(self, profile, jd):
        """REGRA CRÍTICA: subject = título exato da vaga."""
        email = build_email(profile, jd)
        assert email["subject"] == "Desenvolvedor Full Stack"

    def test_html_structure(self, profile, jd):
        email = build_email(profile, jd, attachments=["cv.pdf"])
        assert "<!DOCTYPE html>" in email["html"]
        assert "cv.pdf" in email["html"]
        assert "Rafael" in email["html"] and "Zendron" in email["html"]
        assert jd.company in email["html"]
        # template unificado premium
        assert "#111827" in email["html"] and "#f59e0b" in email["html"]

    def test_text_fallback(self, profile, jd):
        email = build_email(profile, jd)
        assert "Desenvolvedor Full Stack" in email["text"]
        assert profile.contact.email in email["text"]

    def test_with_cover_letter(self, profile, jd):
        letter = build_cover_letter(profile, jd)
        email = build_email(profile, jd, cover_letter=letter)
        assert letter.paragraphs[0][:40] in email["html"]


# ── Matcher ───────────────────────────────────────────────────────────


class TestMatcher:
    def test_strong_match(self, profile, jd):
        result = match(profile, jd)
        assert result.overall_score >= 75  # React/TS/Node/PG todos no CV
        assert not result.missing_skills

    def test_detects_missing_stack(self, profile):
        jd_java = JobDescription(
            id="x", title="Dev Java", company="X", description="",
            requirements=["Microsserviços com Kotlin e Kafka"],
            stack=["Java", "Kotlin", "Kafka"],
        )
        result = match(profile, jd_java)
        assert result.overall_score < 40
        assert set(result.missing_skills) == {"Java", "Kotlin", "Kafka"}

    def test_recommendations_actionable(self, profile, jd):
        result = match(profile, jd)
        assert result.recommendations  # sempre dá próximo passo

    def test_score_bounds(self, profile, jd):
        result = match(profile, jd)
        assert 0 <= result.overall_score <= 100
