"""cv_engine.matching.matcher — match vaga↔CV (BM25 lexical, zero deps).

Score composto:
- skill_coverage: % da stack da vaga presente no CV (peso 50%)
- requirements_coverage: % dos requisitos citados (peso 50%)
Retorna recomendações acionáveis (o que injetar/aprofundar).
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List

from cv_engine.core.models import JobDescription, MatchResult, Profile


_STOPWORDS = {"com", "para", "que", "dos", "das", "por", "uma", "não", "mais", "como",
              "nos", "nas", "aos", "ser", "ter", "seu", "sua", "pelo", "pela",
              "the", "and", "with", "for", "from"}


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-zA-Z+#.]+", text.lower())
            if len(t) > 2 and t not in _STOPWORDS]


def _bm25(query: List[str], doc: List[str], k1: float = 1.5, b: float = 0.75) -> float:
    """BM25 simples single-doc: soma IDF aproximada dos termos presentes."""
    if not query or not doc:
        return 0.0
    doc_counts = Counter(doc)
    score = 0.0
    for term in set(query):
        tf = doc_counts.get(term, 0)
        if tf == 0:
            continue
        # IDF aproximado p/ corpus de 1: log(1 + tf*avgdl/len)
        score += tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(doc) / 200))
    return score


def _cv_fulltext(profile: Profile) -> str:
    parts = [profile.summary, profile.title]
    parts += sum(profile.stack_categories.values(), [])
    for e in profile.experience:
        parts += [e.role, e.description] + e.achievements
    for p in profile.projects:
        parts += [p.name, p.description, p.result] + p.technologies
    for c in profile.certifications:
        parts.append(c.name)
    return " ".join(parts).lower()


def match(profile: Profile, jd: JobDescription) -> MatchResult:
    cv_text = _cv_fulltext(profile)
    cv_tokens = _tokens(cv_text)

    # skill coverage — match com word boundary (evita "java" casar com "javascript")
    def covered(skill: str) -> bool:
        s = re.escape(skill.lower().strip())
        # skill como token inteiro, separadores . / + / # viram fronteiras
        pattern = r"(?<![a-z0-9])" + s.replace(r"\.", r"\.?").replace(r"\+", r"\+?").replace(r"\#", r"#?") + r"(?![a-z0-9])"
        return re.search(pattern, cv_text) is not None

    skill_scores: Dict[str, float] = {}
    for s in jd.stack:
        skill_scores[s] = 100.0 if covered(s) else 0.0

    req_missing: List[str] = []
    req_hits = 0
    for r in jd.requirements:
        key_terms = [t for t in _tokens(r) if len(t) > 2][:5]
        if key_terms and _bm25(key_terms, cv_tokens) > 0:
            req_hits += 1
        else:
            req_missing.append(r)

    skill_cov = (sum(skill_scores.values()) / len(skill_scores)) if skill_scores else 100.0
    req_cov = (req_hits / len(jd.requirements) * 100) if jd.requirements else 100.0
    overall = round(skill_cov * 0.5 + req_cov * 0.5, 1)

    # recomendações acionáveis
    recs: List[str] = []
    missing_stack = [s for s, v in skill_scores.items() if v == 0]
    if missing_stack:
        recs.append(f"Stack da vaga ausente no CV: {', '.join(missing_stack[:5])} — "
                    f"injetar no summary se tiver experiência real")
    if req_missing:
        recs.append(f"Requisitos não cobertos: {req_missing[:3]} — "
                    f"mencionar projetos que os demonstrem")
    if overall >= 75:
        recs.append("Match forte — aplicar com CV tailored + carta citando os 2 projetos top")

    return MatchResult(
        cv_id=profile.name, jd_id=jd.id, overall_score=overall,
        skill_match=skill_scores,
        missing_skills=missing_stack,
        strong_skills=[s for s, v in skill_scores.items() if v == 100],
        keyword_coverage=req_cov,
        semantic_similarity=0.0,  # reservado p/ embeddings (fase 2)
        recommendations=recs,
    )
