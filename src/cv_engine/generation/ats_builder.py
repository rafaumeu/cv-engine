"""cv_engine.generation.ats_builder — gerador de CV ATS-flat.

Regras (baseadas em ats-audit.md + research 2024-2025):
- Single-column, zero grid/flexbox complexo
- HTML semântico: h1 nome, h2 seções, h3 cargos, <time datetime>
- Contatos como links reais (mailto:, tel:)
- Keywords da vaga injetadas no summary como prosa natural
- CSS mínimo inline (Arial), @page A4
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime
from html import escape
from typing import List, Optional

from cv_engine.core.models import Profile


def _period_iso(period: str) -> Optional[str]:
    """'Out 2024 – Presente' -> '2024-10'. Aceita PT/EN."""
    months = {
        "jan": "01", "fev": "01", "mar": "03", "abr": "04", "mai": "05", "jun": "06",
        "jul": "07", "ago": "08", "set": "09", "out": "10", "nov": "11", "dez": "12",
    }
    first = period.split("–")[0].strip().lower()
    parts = first.split()
    if len(parts) == 2 and parts[0][:3] in months:
        return f"{parts[1]}-{months[parts[0][:3]]}"
    return None


def inject_keywords(summary: str, keywords: List[str], max_kw: int = 6) -> str:
    """Injeta keywords da vaga no summary como PROSA NATURAL.

    Calibração V3 (revisão externa): a linha 'Competências alinhadas à vaga:'
    vazava o matcher pro documento — recrutador não deve saber que o CV
    foi adaptado. Agora as keywords são adicionadas como lista simples
    integrada ao texto, sem revelar o mecanismo.
    """
    seen = set()
    missing: List[str] = []
    summary_low = summary.lower()
    for k in keywords:
        k_low = k.lower()
        if k_low in seen or k_low in summary_low:
            continue
        seen.add(k_low)
        missing.append(k)
        if len(missing) >= max_kw:
            break
    if not missing:
        return summary
    return f"{summary} {' | '.join(missing)}."


def _validate_quality(html: str, profile: Profile) -> List[str]:
    """Gate de qualidade — problemas que NUNCA podem aparecer no output.

    Calibração pós-revisão externa (27/09/2026): deteca duplicação de
    termos no summary, contagem de repos, '100% coverage' repetido e
    repetição mecânica de 'Resultado:'.
    """
    issues: List[str] = []
    # 1. Termo duplicado no summary (React ... React) — separador atual é ' | '
    m = re.search(r"([\w+#./ ]+ \| [\w+#./ |]+)\.", html)
    if m and "alinhadas" not in m.group(1):
        terms = [t.strip().lower() for t in m.group(1).split("|")]
        if len(terms) != len(set(terms)):
            issues.append(f"keyword duplicada no summary: {terms}")
    # 1b. Vazamento do matcher no documento (revisão V3)
    if "alinhadas à vaga" in html:
        issues.append("matcher vazando: 'alinhadas à vaga' não pode aparecer no CV")
    # 2. Contagem de repos (métrica fraca — removida por decisão)
    # word boundary: 'monorepo' é legítimo, '127 repos'/'repos públicos' não
    for bad in [r"\d+\s+repos\b", r"\d+\s+repositórios\b", r"repos públicos"]:
        if re.search(bad, html, re.IGNORECASE):
            issues.append(f"contagem de repos no CV: '{bad}' (métrica fraca proibida)")
    # 3. '100% coverage' mais de 1x no documento
    if html.lower().count("100%") > 1:
        issues.append(f"'100%' aparece {html.lower().count('100%')}x (máx 1 — evita 'gaming de cobertura')")
    # 4. Repetição mecânica de 'Resultado:'
    if html.count("Resultado:</strong>") > 2:
        issues.append(f"'Resultado:' repetido {html.count('Resultado:')}x — variar redação")
    # 5. Palavras proibidas pelo tom (revisão: 'obsessivo' agressivo)
    for word in ["obsessivo", "obsessivo por qualidade"]:
        if word in html.lower():
            issues.append(f"tom inadequado: '{word}'")
    # 6. 'em produção' como claim (usar 'Projetos em Destaque')
    if "Projetos em Produção" in html:
        issues.append("seção 'Projetos em Produção' — usar 'Projetos em Destaque' (credibilidade)")
    return issues


def build_ats_cv(profile: Profile, job_title: str = "", keywords: Optional[List[str]] = None) -> str:
    """Gera HTML ATS-flat. job_title = título EXATO da vaga (regra: assunto/título = vaga)."""
    e = escape
    title = e(job_title) if job_title else e(profile.title)
    summary = inject_keywords(profile.summary, keywords or [])

    c = profile.contact
    links = [f'<a href="mailto:{e(c.email)}">{e(c.email)}</a>',
             f'<a href="tel:{e(c.phone.replace(" ", "").replace("(", "").replace(")", ""))}">{e(c.phone)}</a>',
             f'<a href="{e(str(c.linkedin))}">LinkedIn</a>',
             f'<a href="{e(str(c.github))}">GitHub</a>',
             f'<a href="{e(str(c.portfolio))}">Portfólio</a>']

    parts: List[str] = []
    parts.append(f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>{e(profile.name)} — {title}</title>
<meta name="keywords" content="{e(", ".join(sum(profile.stack_categories.values(), [])))}">
<style>
@page {{ size: A4; margin: 14mm 16mm; }}
body {{ font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt; color: #111; line-height: 1.38; }}
h1 {{ font-size: 20pt; margin: 0 0 4px; }}
.headline {{ font-size: 11.5pt; color: #444; margin: 0 0 6px; font-weight: bold; }}
h2 {{ font-size: 12.5pt; margin: 14px 0 5px; border-bottom: 1px solid #999; padding-bottom: 2px; }}
h3 {{ font-size: 11pt; margin: 8px 0 2px; }}
p, li {{ margin: 2px 0; }}
ul {{ margin: 4px 0; padding-left: 18px; }}
.contact a {{ color: #111; text-decoration: none; }}
.job, .proj {{ margin-bottom: 10px; }}
/* V3: impede orphan heading — título nunca fica sozinho no fim da página */
.job, .proj, h2 + ul, h3 {{ break-inside: avoid; page-break-inside: avoid; }}
.jd {{ color: #444; }}
</style>
</head>
<body>
<h1>{e(profile.name)}</h1>
<p class="headline">{e(profile.headline or profile.title)}</p>
<p class="contact">{' | '.join(links)} | {e(c.location)}{f' | {e(c.availability)}' if c.availability else ''}</p>
<h2>Resumo Profissional</h2>
<p>{e(summary)}</p>""")

    # Competências Técnicas — TODAS as categorias (indexação ATS crítica;
    # V2 perdera front/backend/dados por mapear labels antigos)
    parts.append('<h2>Competências Técnicas</h2>')
    labels = {"languages": "Linguagens", "frontend": "Front-end", "backend": "Back-end",
              "data": "Dados", "testing": "Testes", "devops": "DevOps",
              "architecture": "Arquitetura", "ai_automation": "IA e Automação",
              "infra": "Infra/Filas",
              # fallback: categorias antigas
              "frameworks": "Front-end", "databases": "Dados", "tools": "Ferramentas",
              "cloud": "DevOps", "architectures": "Arquitetura"}
    for key, label in labels.items():
        items = profile.stack_categories.get(key, [])
        if items:
            parts.append(f'<p><strong>{label}:</strong> {e(", ".join(items))}</p>')

    # Experiência — sem duplicação (ou description OU bullets, nunca ambos)
    parts.append('<h2>Experiência Profissional</h2>')
    for job in profile.experience:
        iso = _period_iso(job.period)
        time_attr = f' datetime="{iso}"' if iso else ""
        parts.append(f'<article class="job"><h3>{e(job.role)}</h3>'
                     f'<p class="jd">{e(job.company)} — <time{time_attr}>{e(job.period)}</time></p>')
        if job.achievements:
            parts.append("<ul>" + "".join(f"<li>{e(a)}</li>" for a in job.achievements) + "</ul>")
        elif job.description:
            parts.append(f'<p>{e(job.description)}</p>')
        parts.append("</article>")

    # Projetos em Destaque — apenas featured (máx 5); demais viram 1 linha
    parts.append('<h2>Projetos em Destaque</h2>')
    featured = [p for p in profile.projects if getattr(p, "featured", False)]
    others = [p for p in profile.projects if not getattr(p, "featured", False)]
    for p in featured:
        url = f' — <a href="{e(str(p.url))}">{e(str(p.url)).replace("https://", "")}</a>' if p.url else ""
        parts.append(f'<article class="proj"><h3>{e(p.name)}</h3>'
                     f'<p>{e(p.description)}</p>'
                     f'<p>{e(p.result)}</p>'
                     f'<p class="jd">{e(", ".join(p.technologies))}{url}</p></article>')
    if others:
        names = ", ".join(p.name for p in others)
        parts.append(f'<p class="jd">Outros projetos: {e(names)} — <a href="{e(str(profile.contact.github))}">github.com/rafaumeu</a></p>')

    # Formação Acadêmica — só graduação (cursos vão em Formação Complementar)
    parts.append('<h2>Formação Acadêmica</h2><ul>')
    for ed in profile.education:
        parts.append(f'<li>{e(ed.course)} — {e(ed.institution)} ({e(ed.status)})</li>')
    parts.append('</ul>')

    # Formação Complementar (cursos)
    complementary = getattr(profile, "complementary_education", None)
    if complementary:
        parts.append('<h2>Formação Complementar</h2><ul>')
        for ced in complementary:
            parts.append(f'<li>{e(ced["course"])} — {e(ced["institution"])} ({e(ced["status"])})</li>')
        parts.append('</ul>')

    # Certificações — compactas (lista longa vira página de lista; feedback r5)
    parts.append('<h2>Certificações</h2>')
    cert_lines = [cert.render() for cert in profile.certifications]
    parts.append('<p>' + e(' · '.join(cert_lines)) + '</p>')
    footnote = getattr(profile, "certifications_footnote", None)
    if footnote:
        parts.append(f'<p class="jd">{e(footnote)}</p>')

    # Idiomas
    if profile.languages:
        parts.append('<h2>Idiomas</h2><ul>')
        for lang in profile.languages:
            parts.append(f'<li>{e(lang)}</li>')
        parts.append('</ul>')

    parts.append('</body></html>')
    html = "\n".join(parts)

    # GATE DE QUALIDADE — falha ruidosamente se violar regras de calibração
    issues = _validate_quality(html, profile)
    if issues:
        raise ValueError("CV viola gate de qualidade: " + "; ".join(issues))
    return html


def sha256_of(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def generation_meta(content: str, template: str, filename: str) -> dict:
    return {
        "filename": filename,
        "template": template,
        "bytes_size": len(content.encode()),
        "generated_at": datetime.now().isoformat(),
        "sha256": sha256_of(content),
    }
