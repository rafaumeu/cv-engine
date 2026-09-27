"""Testes do dossiê de fit — vereditos incisivos."""
from __future__ import annotations

from pathlib import Path

import pytest

from cv_engine.core.dossier import Verdict, build_dossier
from cv_engine.core.models import JobDescription, Profile

BASE = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def profile() -> Profile:
    return Profile.from_json_file(str(BASE / "data" / "profile-rafael-zendron.json"))


def _jd(**kw) -> JobDescription:
    base = dict(id="t", title="Dev Full Stack", company="X", description="",
                requirements=[], stack=[])
    base.update(kw)
    return JobDescription(**base)


class TestDossier:
    def test_strong_match_applies(self, profile):
        """Vaga React/TS/Node/PG = match total → APLICA."""
        d = build_dossier(profile, _jd(
            requirements=["React e TypeScript", "APIs REST", "Testes automatizados"],
            stack=["React", "TypeScript", "Node.js", "PostgreSQL"]))
        assert d.verdict == Verdict.APPLY
        assert d.selling_points
        assert not d.honest_gaps
        assert "Alta" in d.salary_leverage

    def test_gap_stack_honest(self, profile):
        """Vaga Java/Kafka = gap real declarado, sem maquiagem."""
        d = build_dossier(profile, _jd(
            stack=["Java", "Kotlin", "Kafka"],
            requirements=["Microsserviços com Kotlin"]))
        assert d.verdict == Verdict.SKIP
        assert any("Java" in g for g in d.honest_gaps)
        assert "Baixa" in d.salary_leverage

    def test_senior_role_flagged(self, profile):
        """Vaga sênior gera gap honesto de senioridade."""
        d = build_dossier(profile, _jd(
            title="Desenvolvedor Sênior Full Stack",
            stack=["React", "TypeScript"]))
        assert any("sênior" in g.lower() for g in d.honest_gaps)

    def test_years_requirement_flagged(self, profile):
        """Requisito 'X anos de experiência' gera gap + orientação honesta."""
        d = build_dossier(profile, _jd(
            stack=["React"],
            requirements=["5 anos de experiência com React"]))
        assert any("anos" in g for g in d.honest_gaps)

    def test_prep_actionable(self, profile):
        """Prep sempre dá próximo passo concreto, nunca vago."""
        d = build_dossier(profile, _jd(
            stack=["React", "Rust"],
            requirements=["APIs REST"]))
        assert d.prep_before_applying
        assert any(len(p) > 20 for p in d.prep_before_applying)

    def test_pitch_cites_real_project(self, profile):
        """Pitch cita projeto real com métrica — nunca frase genérica."""
        d = build_dossier(profile, _jd(
            stack=["React", "TypeScript"]))
        assert d.pitch_line
        # menciona nome de projeto real do profile
        assert any(p.name.lower() in d.pitch_line.lower() or
                   p.name.split()[0].lower() in d.pitch_line.lower()
                   for p in profile.projects)

    def test_confidence_bounds(self, profile):
        d = build_dossier(profile, _jd(stack=["React"], requirements=["React"]))
        assert 0 <= d.confidence <= 100
