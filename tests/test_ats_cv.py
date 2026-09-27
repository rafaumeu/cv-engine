"""Testes de regressão: profile real + gerador ATS-flat.

Estes testes validam o CONTRATO: dados reais carregam sem erro,
HTML gerado é parseável (estrutura semântica que ATS exige).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from cv_engine.core.models import Profile
from cv_engine.generation.ats_builder import build_ats_cv, inject_keywords, sha256_of

BASE = Path(__file__).resolve().parent.parent
PROFILE_JSON = BASE / "data" / "profile-rafael-zendron.json"


@pytest.fixture(scope="module")
def profile() -> Profile:
    return Profile.from_json_file(str(PROFILE_JSON))


# ── Profile real (zero alucinação) ────────────────────────────────────


class TestProfileReal:
    def test_loads(self, profile):
        assert profile.name == "Rafael Dias Zendron"
        assert profile.title == "Full Stack Developer"

    def test_metrics_real(self, profile):
        """Métricas do projeto principal — NUNCA inventadas (padrão BR 1.900)."""
        tesouros = next(p for p in profile.projects if "Tesouros" in p.name)
        assert "1.900+" in tesouros.result or "1900+" in tesouros.result

    def test_projects_have_result(self, profile):
        """Todo projeto TEM métrica mensurável (regra recruiter)."""
        for p in profile.projects:
            assert p.result.strip(), f"projeto {p.name} sem resultado"

    def test_no_cliche_summary(self, profile):
        """Clichês PROIBIDOS (recruitment-quality-framework)."""
        cliches = ["proativo", "dinâmico", "apaixonado por tecnologia",
                   "profissional comprometido", "especialista em"]
        for c in cliches:
            assert c not in profile.summary.lower()

    def test_contact_complete(self, profile):
        assert profile.contact.email
        assert profile.contact.github
        assert profile.contact.linkedin

    def test_dates_honest(self, profile):
        """Experiências tech: Projetos Independentes + contribuições com PRs merged.
        Nunca 'X anos' inflado — datas verificáveis no GitHub."""
        tech = [e for e in profile.experience if e.is_tech]
        assert len(tech) == 2
        assert tech[0].period.startswith("2025")   # pianolouvorja/kidev-tec
        assert tech[1].period.startswith("Out 2024")  # projetos independentes

    def test_chronology_against_linkedin(self, profile):
        """Regressão (bug pego pelo Rafael): linha do tempo SEM buracos.

        Fonte da verdade: LinkedIn (27/09/2026). De Bem Tintas (fev/2021–
        dez/2023) existia no LinkedIn mas faltava no CV, criando gap 2020-2024.
        """
        non_tech = {(e.company, e.period) for e in profile.experience if not e.is_tech}
        # cada período verificado tem que estar presente (por empresa)
        companies = {c for c, _ in non_tech}
        for expected in ["Teleperformance", "De Bem Tintas", "Tempo USS"]:
            assert any(expected in c for c in companies), f"empresa ausente: {expected}"

        # ordenação: mais recente primeiro (contribuições 2025-Presente)
        periods = [e.period for e in profile.experience]
        assert periods[0].startswith("2025")   # pianolouvorja/kidev-tec atual
        assert periods[1].startswith("Out 2024")  # projetos independentes

        # sem sobreposição nem gap 2020-2024: De Bem Tintas cobre
        debem = next(e for e in profile.experience if "De Bem" in e.company)
        assert debem.start.year == 2021 and debem.end.year == 2023


# ── ATS-flat output ───────────────────────────────────────────────────


class TestATSCV:
    def test_generates(self, profile):
        html = build_ats_cv(profile)
        assert "<!DOCTYPE html>" in html
        assert profile.name in html

    def test_semantic_structure(self, profile):
        """h1 nome, h2 seções, h3 cargos, time, links de contato."""
        html = build_ats_cv(profile)
        assert "<h1>" in html
        for section in ["Resumo Profissional", "Competências Técnicas",
                        "Experiência Profissional", "Projetos em Destaque",
                        "Formação Acadêmica", "Certificações"]:
            assert f"<h2>{section}</h2>" in html, f"seção ausente: {section}"
        assert html.count("<h3>") == len(profile.experience) + len([p for p in profile.projects if p.featured])
        assert "<time " in html
        assert "mailto:" in html and "tel:" in html

    def test_job_title_exact(self, profile):
        """Título do doc = título EXATO da vaga (regra: assunto/título = vaga)."""
        html = build_ats_cv(profile, job_title="Desenvolvedor Full Stack Pleno")
        assert "<title>Rafael Dias Zendron — Desenvolvedor Full Stack Pleno</title>" in html

    def test_no_grid_no_external_fonts(self, profile):
        """Zero CSS grid, zero @import (quebram ATS parsers)."""
        html = build_ats_cv(profile)
        assert "grid-template" not in html
        assert "@import" not in html

    def test_keyword_injection(self, profile):
        """Keywords ausentes aparecem no summary; presentes NÃO duplicam."""
        html = build_ats_cv(profile, keywords=["Kafka", "GraphQL"])
        text = re.sub(r"<[^>]+>", " ", html)
        assert "Kafka" in text and "GraphQL" in text
        assert "alinhadas à vaga" not in html  # matcher não vaza no documento
        # sem duplicatas
        tail = text[text.find("IA e Automação"):] if "IA e Automação" in text else text[-400:]
        terms = [t.strip().lower() for t in tail.split("|")]
        assert len(terms) == len(set(terms))

    def test_no_duplicate_term_in_summary(self, profile):
        """Regressão: 'React ... React' no summary (bug pego em revisão externa)."""
        html = build_ats_cv(profile, keywords=["React", "React", "Kafka", "GraphQL"])
        text = re.sub(r"<[^>]+>", " ", html)
        # React presente UMA vez no trecho de keywords (dedup funcionou)
        idx = text.find("GraphQL")
        assert idx > -1
        tail = text[idx-200:idx+50]
        assert tail.lower().count("react") <= 1

    def test_headline_visible(self, profile):
        """V3: headline abaixo do nome — posicionamento em 2 segundos."""
        html = build_ats_cv(profile)
        assert "Desenvolvedor Full Stack | TypeScript | React | Node.js" in html

    def test_no_orphan_heading(self, profile):
        """V3: break-inside avoid — título nunca órfão no fim da página."""
        html = build_ats_cv(profile)
        assert "break-inside: avoid" in html

    def test_skills_complete(self, profile):
        """V3: TODAS as categorias de stack presentes (indexação ATS)."""
        html = build_ats_cv(profile)
        for cat_items in [("Linguagens", "TypeScript"), ("Front-end", "React"),
                          ("Back-end", "Node.js"), ("Dados", "PostgreSQL"),
                          ("Testes", "Vitest"), ("DevOps", "Docker"),
                          ("Arquitetura", "Clean Architecture"),
                          ("IA e Automação", "LLMs")]:
            assert f"<strong>{cat_items[0]}:</strong>" in html, f"categoria ausente: {cat_items[0]}"
            assert cat_items[1] in html

    def test_deterministic(self, profile):
        """Mesmo input = mesmo output (regressão por SHA-256)."""
        h1 = sha256_of(build_ats_cv(profile))
        h2 = sha256_of(build_ats_cv(profile))
        assert h1 == h2

    def test_text_extractable(self, profile):
        """Simula extração de texto ATS: tags fora, conteúdo dentro."""
        html = build_ats_cv(profile)
        text = re.sub(r"<[^>]+>", " ", html)
        for expected in ["Rafael Dias Zendron", "Tesouros de Jaú",
                         "1.900+ testes automatizados", "Estácio"]:
            assert expected in text
