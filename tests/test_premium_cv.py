"""Testes do template Premium V3 (linear, amber+black)."""
from __future__ import annotations

from pathlib import Path

import pytest

from cv_engine.core.models import Profile
from cv_engine.generation.premium_builder import build_premium_cv

BASE = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def profile() -> Profile:
    return Profile.from_json_file(str(BASE / "data" / "profile-rafael-zendron.json"))


class TestPremiumCV:
    def test_generates(self, profile):
        html = build_premium_cv(profile)
        assert "<!DOCTYPE html>" in html
        assert profile.name in html

    def test_dark_header_amber(self, profile):
        html = build_premium_cv(profile)
        assert "#111827" in html and "#f59e0b" in html

    def test_linear_flow_no_sidebar(self, profile):
        """V3 gauntlet: SEM sidebar — ordem de extração linear (bug ATS r1)."""
        html = build_premium_cv(profile)
        assert "grid-template-columns: 2fr 1fr" not in html  # sidebar morta

    def test_section_order_matches_ats(self, profile):
        """V3 gauntlet: ordem das seções no HTML = ordem de leitura do ATS."""
        html = build_premium_cv(profile)
        order = ["Competências Técnicas", "Experiência",
                 "Projetos em Destaque", "Formação Acadêmica", "Certificações"]
        pos = [html.find(s) for s in order]
        assert all(p > -1 for p in pos), f"seção ausente: {[s for s, p in zip(order, pos) if p == -1]}"
        assert pos == sorted(pos), f"ordem quebrada: {list(zip(order, pos))}"

    def test_no_project_split(self, profile):
        """V3 gauntlet: break-inside avoid — projeto nunca quebra entre páginas."""
        html = build_premium_cv(profile)
        assert "break-inside: avoid" in html

    def test_headline_in_header(self, profile):
        html = build_premium_cv(profile)
        assert "Desenvolvedor Full Stack | TypeScript | React | Node.js" in html

    def test_stack_complete(self, profile):
        """Sidebar V2 só mostrava Linguagens — agora todas as categorias."""
        html = build_premium_cv(profile)
        for label in ["Linguagens", "Front-end", "Back-end", "Dados",
                      "Testes", "DevOps", "Arquitetura", "IA e Automação"]:
            assert f"<strong>{label}:</strong>" in html

    def test_semantic_time(self, profile):
        html = build_premium_cv(profile)
        assert "<time " in html

    def test_deterministic(self, profile):
        assert build_premium_cv(profile) == build_premium_cv(profile)
