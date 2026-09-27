"""cv_engine.core.dossier — dossiê de fit: candidata ou não?

Incisivo, sem enrolação. Combina o score do matcher com regras de
decisão (gaps vs requisitos, senioridade, honestidade sobre lacunas).
Saída: veredito + argumentos de venda + riscos + o que prepar.
"""
from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field

from cv_engine.core.models import JobDescription, MatchResult, Profile
from cv_engine.matching.matcher import match


class Verdict(str, Enum):
    APPLY = "APLICA"
    APPLY_WITH_GAPS = "APLICA COM RESSALVAS"
    SKIP = "NÃO CANDIDATA"


class Dossier(BaseModel):
    verdict: Verdict
    confidence: int = Field(ge=0, le=100)
    match_score: float
    selling_points: List[str]          # por que VOCÊ é forte p/ esta vaga
    honest_gaps: List[str]             # o que você NÃO tem (sem maquiagem)
    prep_before_applying: List[str]    # o que fazer ANTES de enviar
    pitch_line: str                    # frase de abertura da cover letter
    salary_leverage: str               # leitura de poder de negociação


# Limiares de decisão
_STRONG = 75
_WEAK = 45


def build_dossier(profile: Profile, jd: JobDescription) -> Dossier:
    result = match(profile, jd)
    selling: List[str] = []
    gaps: List[str] = []
    prep: List[str] = []

    # ── Selling points (fatos do profile que batem com a vaga) ──
    strong = [s for s, v in result.skill_match.items() if v == 100]
    if strong:
        selling.append(f"Stack core 100% coberta: {', '.join(strong)}")
    if result.keyword_coverage >= 60:
        selling.append(f"{result.keyword_coverage:.0f}% dos requisitos citados no seu histórico")

    has_tests = "testes" in _fulltext(profile)
    if has_tests and any("test" in r.lower() for r in jd.requirements):
        selling.append("Vaga pede testes — você tem 2.700+ com 100% coverage (raro entre candidatos BR)")

    arch = profile.stack_categories.get("architectures", [])
    if any(a.lower() in _fulltext(profile) for a in ["clean architecture", "ddd"]):
        selling.append(f"Arquitetura formal ({', '.join(arch[:2])}) — diferencia pleno de júnior")

    if result.overall_score >= _STRONG:
        selling.append("Perfil raro para a vaga: match quase total")

    # ── Gaps honestos ──
    if result.missing_skills:
        gaps.append(f"Stack ausente no seu histórico: {', '.join(result.missing_skills)} "
                    f"(NÃO invente experiência — assuma no pitch ou aprenda antes)")
    for r in jd.requirements:
        low = r.lower()
        if any(w in low for w in ["anos de experiência", "anos experiência"]):
            gaps.append(f"Requisito de tempo: '{r}' — sua experiência tech formal é Out/2024–hoje; "
                        "compensa com volume de produção (3 SaaS, 2.700 testes), nunca com número inflado")

    # Senioridade: vaga sênior não é target honesto pro perfil atual
    if any(w in (jd.title + jd.description).lower() for w in ["sênior", "senior", "sr."]):
        gaps.append("Vaga sênior — seu nível é pleno; aplicar direto enfraquece outras candidaturas")

    # ── Prep ──
    if result.missing_skills:
        prep.append(f"Antes de aplicar: 1 projeto pequeno público com {result.missing_skills[0]} "
                    "vale mais que citar a palavra no CV")
    if gaps:
        prep.append("Prepare resposta para o gap na entrevista — o recrutador VAI perguntar")
    if result.overall_score >= _STRONG:
        prep.append("Destaque os 2 projetos mais próximos do domínio da vaga no topo do CV")

    # ── Veredito ──
    if result.overall_score >= _STRONG and not gaps:
        verdict = Verdict.APPLY
        confidence = min(95, int(result.overall_score))
    elif result.overall_score >= _WEAK and len(gaps) <= 2:
        verdict = Verdict.APPLY_WITH_GAPS
        confidence = int(result.overall_score)
    else:
        verdict = Verdict.SKIP
        confidence = 100 - int(result.overall_score)

    # ── Pitch ──
    # projeto com produto real > genérico (exclui "Open Source" e "meta")
    real = [p for p in profile.projects
            if "open source" not in p.name.lower() and "meta" not in p.name.lower()]
    top_project = real[0] if real else profile.projects[0]
    pitch_line = (f"Construí {top_project.name} com {top_project.result.split(',')[0].lower()} — "
                  f"é exatamente o tipo de problema que esta vaga resolve.")

    # ── Leverage ──
    if verdict == Verdict.APPLY:
        lev = ("Alta: match quase total. Peça a faixa primeiro; você é o perfil difícil de encontrar.")
    elif verdict == Verdict.APPLY_WITH_GAPS:
        lev = ("Média: você passa no core mas tem lacunas. Negocie por potencial de growth, "
               "não por escassez.")
    else:
        lev = ("Baixa: aplicar queima capital (recrutadores lembram de matches ruins). "
               "Guarde para vagas com fit real.")

    return Dossier(
        verdict=verdict, confidence=confidence, match_score=result.overall_score,
        selling_points=selling or ["Match técnico básico — sem diferencial forte identificado"],
        honest_gaps=gaps, prep_before_applying=prep,
        pitch_line=pitch_line, salary_leverage=lev,
    )


def _fulltext(profile: Profile) -> str:
    parts = [profile.summary]
    parts += sum(profile.stack_categories.values(), [])
    for p in profile.projects:
        parts += [p.description, p.result]
    return " ".join(parts).lower()
