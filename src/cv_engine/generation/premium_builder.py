"""cv_engine.generation.premium_builder — CV visual (amber+black).

V3 (gauntlet r2): FLUXO LINEAR de coluna única.
A sidebar de 2 colunas quebrava a ordem de extração do PDF (ATS lia
STACK/FORMAÇÃO no meio de um projeto). Mantém o visual premium
(header dark, accents amber, cards de resultado) mas em ordem linear:
Competências → Resumo → Experiência → Projetos → Formação → Certificações.
"""
from __future__ import annotations

from html import escape
from typing import Optional

from cv_engine.core.models import Profile
from cv_engine.generation.ats_builder import _period_iso, inject_keywords

_LABELS = {
    "languages": "Linguagens", "frontend": "Front-end", "backend": "Back-end",
    "data": "Dados", "testing": "Testes", "devops": "DevOps",
    "architecture": "Arquitetura", "ai_automation": "IA e Automação",
    "infra": "Infra/Filas",
    # fallback categorias antigas
    "frameworks": "Front-end", "databases": "Dados", "tools": "Ferramentas",
    "cloud": "DevOps", "architectures": "Arquitetura",
}


def build_premium_cv(profile: Profile, job_title: str = "",
                     keywords: Optional[list] = None) -> str:
    e = escape
    title = e(job_title) if job_title else e(profile.title)
    summary = inject_keywords(profile.summary, keywords or [])
    c = profile.contact

    h = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>{e(profile.name)} — {title}</title>
<style>
@page {{ size: A4; margin: 0; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: Arial, Helvetica, sans-serif; color: #1f2937; font-size: 10.5pt; line-height: 1.45; }}
.header {{ background: #111827; color: #fff; padding: 26px 36px 20px; border-bottom: 4px solid #f59e0b; }}
.header h1 {{ font-size: 22pt; letter-spacing: 0.5px; }}
.header .headline {{ color: #f59e0b; font-size: 11.5pt; margin-top: 3px; font-weight: bold; }}
.header .contact {{ color: #9ca3af; font-size: 9.5pt; margin-top: 9px; }}
.header .contact a {{ color: #d1d5db; text-decoration: none; }}
.body {{ padding: 20px 36px; }}
h2 {{ font-size: 12pt; color: #111827; border-bottom: 2px solid #f59e0b; padding-bottom: 3px;
   margin: 15px 0 7px; text-transform: uppercase; letter-spacing: 1px;
   break-after: avoid; page-break-after: avoid; }}
h3 {{ font-size: 11pt; margin: 9px 0 1px; }}
.stack p {{ margin: 2px 0; font-size: 9.5pt; }}
.stack strong {{ color: #b45309; }}
.job, .proj {{ margin-bottom: 9px; break-inside: avoid; page-break-inside: avoid; }}
.job-meta {{ color: #6b7280; font-size: 9.5pt; margin-bottom: 3px; }}
.job-meta time {{ color: #b45309; font-weight: bold; }}
ul {{ margin: 3px 0 3px 16px; }}
li {{ margin: 2px 0; }}
.result {{ background: #fef3c7; border-left: 3px solid #f59e0b; padding: 4px 8px;
   margin: 4px 0; font-size: 9.5pt; }}
.summary {{ background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px;
   padding: 11px 14px; margin-bottom: 4px; }}
a {{ color: #b45309; }}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px 24px; }}
</style></head><body>
<div class="header">
  <h1>{e(profile.name)}</h1>
  <div class="headline">{e(profile.headline or title)}</div>
  <div class="contact">{e(c.email)} · {e(c.phone)} · {e(c.location)}{f' · {e(c.availability)}' if c.availability else ''} ·
  <a href="{e(str(c.github))}">github.com/rafaumeu</a> ·
  <a href="{e(str(c.linkedin))}">LinkedIn</a> ·
  <a href="{e(str(c.portfolio))}">Portfólio</a></div>
</div>
<div class="body">"""

    # Stack ANTES do resumo (leitura: quem sou → com quê → o que fiz)
    h += '<h2>Competências Técnicas</h2><div class="stack two-col">'
    seen_keys = set()
    for key, label in _LABELS.items():
        if key in seen_keys:
            continue
        seen_keys.add(key)
        items = profile.stack_categories.get(key, [])
        if items:
            h += f"<p><strong>{label}:</strong> {e(', '.join(items))}</p>"
    h += "</div>"

    h += f'<div class="summary"><p>{e(summary)}</p></div>'

    h += '<h2>Experiência</h2>'
    for job in profile.experience:
        iso = _period_iso(job.period)
        time_attr = f' datetime="{iso}"' if iso else ""
        h += (f'<div class="job"><h3>{e(job.role)}</h3>'
              f'<p class="job-meta">{e(job.company)} — <time{time_attr}>{e(job.period)}</time></p>')
        if job.achievements:
            h += "<ul>" + "".join(f"<li>{e(a)}</li>" for a in job.achievements) + "</ul>"
        elif job.description:
            h += f'<p>{e(job.description)}</p>'
        h += "</div>"

    h += '<h2>Projetos em Destaque</h2>'
    featured = [p for p in profile.projects if getattr(p, "featured", True)]
    others = [p for p in profile.projects if not getattr(p, "featured", True)]
    for p in featured:
        url = (f' — <a href="{e(str(p.url))}">{e(str(p.url)).replace("https://", "")}</a>'
               if p.url else "")
        h += (f'<div class="proj"><h3>{e(p.name)}</h3>'
              f'<p>{e(p.description)}</p>'
              f'<p class="result"><strong>{e(p.result)}</strong></p>'
              f'<p class="job-meta">{e(" · ".join(p.technologies))}{url}</p></div>')
    if others:
        names = ", ".join(p.name for p in others)
        h += (f'<p class="job-meta">Outros projetos: {e(names)} — '
              f'<a href="{e(str(profile.contact.github))}">github.com/rafaumeu</a></p>')

    h += '<h2>Formação Acadêmica</h2><ul>'
    for ed in profile.education:
        h += f"<li>{e(ed.course)} — {e(ed.institution)} ({e(ed.status)})</li>"
    h += "</ul>"

    complementary = getattr(profile, "complementary_education", None)
    if complementary:
        h += '<h2>Formação Complementar</h2><ul>'
        for ced in complementary:
            h += f"<li>{e(ced['course'])} — {e(ced['institution'])} ({e(ced['status'])})</li>"
        h += "</ul>"

    h += '<h2>Certificações</h2>'
    cert_lines = [cert.render() for cert in profile.certifications]
    h += f'<p>{e(" · ".join(cert_lines))}</p>'
    footnote = getattr(profile, "certifications_footnote", None)
    if footnote:
        h += f'<p class="job-meta">{e(footnote)}</p>'

    if profile.languages:
        h += '<h2>Idiomas</h2><ul>'
        for lang in profile.languages:
            h += f"<li>{e(lang)}</li>"
        h += "</ul>"

    h += "</div></body></html>"
    return h
