"""cv_engine.generation.cover_letter — carta de apresentação (3 parágrafos).

Padrão recruitment-quality-framework:
- P1 Hook: projeto mais impressionante OU conexão com missão da empresa
- P2 Prova: projetos PELO NOME com 1+ número cada
- P3 Fechamento ATIVO: propõe próximo passo concreto
- Máx 350 palavras, zero "Venho por meio desta"
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from cv_engine.core.models import JobDescription, Profile


@dataclass
class CoverLetter:
    subject: str
    paragraphs: List[str]
    metrics_cited: List[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(self.paragraphs)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def validate(self) -> List[str]:
        """Regras do framework — retorna violações (vazio = OK)."""
        issues = []
        if self.word_count > 350:
            issues.append(f"carta com {self.word_count} palavras (máx 350)")
        if len(self.paragraphs) != 3:
            issues.append(f"{len(self.paragraphs)} parágrafos (esperado 3)")
        banned = ["venho por meio desta", "escrevo com entusiasmo",
                  "fico à disposição", "ao longo da minha trajetória"]
        low = self.text.lower()
        for b in banned:
            if b in low:
                issues.append(f"clichê proibido: '{b}'")
        if not self.metrics_cited:
            issues.append("nenhuma métrica citada (prova fraca)")
        return issues


def _find_projects(profile: Profile, jd: JobDescription, max_projects: int = 2):
    """Projetos mais relevantes pra vaga: ordena por overlap de stack."""
    jd_tokens = {t.lower() for t in jd.stack + jd.requirements}
    scored = []
    for p in profile.projects:
        overlap = len({t.lower() for t in p.technologies} & jd_tokens)
        scored.append((overlap, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:max_projects]]


def build_cover_letter(profile: Profile, jd: JobDescription,
                       custom_hook: Optional[str] = None,
                       spontaneous: bool = False) -> CoverLetter:
    """spontaneous=True: candidatura espontânea (sem vaga anunciada).

    Não presume vaga aberta; apresenta o perfil para oportunidades
    atuais ou futuras (feedback ChatGPT — não pedir emprego 'no escuro').
    """
    projects = _find_projects(profile, jd)
    metrics: List[str] = []

    # P1 — Hook
    if spontaneous:
        p1 = (f"Gostaria de me apresentar e deixar meu perfil à disposição da {jd.company} "
              f"para oportunidades atuais ou futuras em desenvolvimento de software.")
    elif custom_hook:
        p1 = custom_hook
    elif projects:
        p = projects[0]
        p1 = (f"A {jd.company} busca um {jd.title}, e o que construí se conecta "
              f"diretamente a esse desafio: {p.name.lower()}, {p.description.split('—')[0].strip().lower()}.")
    else:
        p1 = (f"Desenvolvedor Full Stack com experiência em "
              f"{', '.join(profile.stack_categories.get('frameworks', []))} aplicada a produtos reais.")

    # P2 — Prova (projetos pelo nome, 1+ número cada)
    metric_re = re.compile(
        r"\d+\+?\s*(?:testes|API routes|scrapers|tabelas|repositórios|repos)"
        r"|\d+%\s*[a-zà-ú ]+"
        r"|\d+\+?\s*(?:stars|PRs|pull requests)")
    proofs = []
    for p in projects:
        m = metric_re.search(p.result)
        if m:
            metrics.append(m.group(0))
        # capitaliza só a 1ª letra se a 2ª for minúscula (preserva siglas: PRs, DDD, CI)
        head = p.result[0]
        rest_keeps_case = p.result[1:2].isupper()
        proof = p.result if rest_keeps_case else head.lower() + p.result[1:]
        proofs.append(f"{p.name}: {proof}")
    if spontaneous:
        p2 = ("Estou em transição profissional para desenvolvimento Full Stack, construindo experiência "
              "prática com TypeScript, React, Node.js, PostgreSQL, testes automatizados e CI/CD. "
              + "Evidência — " + "; ".join(proofs)
              + ". Também somo mais de 100 pull requests merged em repositórios públicos.")
    else:
        p2 = "Evidência em produção — " + "; ".join(proofs) + "."

    # P3 — Fechamento ativo
    if spontaneous:
        p3 = (f"Não sei se a {jd.company} possui uma posição aberta neste momento, mas deixo meu "
              f"currículo e GitHub para consideração caso meu perfil faça sentido para alguma "
              f"necessidade atual ou futura da equipe. Fico à disposição para apresentar meu código, "
              f"projetos e decisões técnicas em mais detalhes.")
    else:
        p3 = (f"Posso enviar o repositório do {projects[0].name} ou um walkthrough do código "
              f"nos próximos dias, antes de qualquer entrevista — é o modo mais rápido de "
              f"avaliar como escrevo software.")

    subject = (f"Candidatura espontânea — {jd.title}" if spontaneous else jd.title)
    return CoverLetter(subject=subject, paragraphs=[p1, p2, p3], metrics_cited=metrics)


def render_html(letter: CoverLetter, profile: Profile, jd=None) -> str:
    """Carta no template premium (amber+dark, idêntico ao CV visual).

    Pdf-ready: A4 com header dark + accent amber, mesma identidade do CV.
    jd opcional: preenche a meta-bar 'Para: empresa'.
    """
    import html as _h
    from datetime import date

    e = _h.escape
    c = profile.contact
    nome = profile.name.split(" ")
    first, last = " ".join(nome[:-1]), nome[-1]
    hoje = date.today().strftime("%d/%m/%Y")
    meta = (f'<span>Para: {e(jd.company)}</span><span>{hoje}</span>' if jd
            else f'<span>{hoje}</span>')
    re_line = f'Re: {e(letter.subject)}'

    ps = "".join(f'<p style="margin:0 0 14px;">{e(p)}</p>' for p in letter.paragraphs)

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Carta de Apresentação — {e(profile.name)}</title>
<style>
@page {{ size: A4; margin: 0; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: Arial, Helvetica, sans-serif; color: #1f2937; font-size: 11pt; line-height: 1.55; }}
.header {{ background: #111827; color: #fff; padding: 26px 36px 20px; border-bottom: 4px solid #f59e0b; }}
.header h1 {{ font-size: 22pt; letter-spacing: 0.5px; }}
.header h1 span {{ color: #f59e0b; }}
.header .role {{ color: #9ca3af; font-size: 10.5pt; margin-top: 3px; }}
.header .contacts {{ color: #9ca3af; font-size: 9.5pt; margin-top: 9px; }}
.header .contacts a {{ color: #d1d5db; text-decoration: none; }}
.meta-bar {{ display: flex; justify-content: space-between; background: #f9fafb;
   border-bottom: 1px solid #e5e7eb; padding: 10px 36px; font-size: 9.5pt; color: #6b7280; }}
.body {{ padding: 28px 36px; }}
.recipient {{ margin-bottom: 20px; font-size: 10.5pt; }}
.recipient strong {{ display: block; color: #111827; }}
.recipient .re {{ color: #6b7280; }}
p {{ margin: 0 0 14px; }}
.closing {{ margin-top: 28px; display: flex; justify-content: space-between; align-items: end; }}
.sign-name {{ font-weight: bold; color: #111827; font-size: 12pt; }}
.sign-sub {{ color: #6b7280; font-size: 9.5pt; }}
.cta-tag {{ background: #fef3c7; border-left: 3px solid #f59e0b; padding: 6px 12px;
   font-size: 9.5pt; color: #92400e; }}
.footer {{ background: #111827; color: #9ca3af; padding: 14px 36px; font-size: 9pt;
   display: flex; gap: 8px; }}
.footer a {{ color: #d1d5db; text-decoration: none; }}
</style></head><body>
<div class="header">
  <h1>{e(first)} <span>{e(last)}</span></h1>
  <div class="role">{e(profile.headline or profile.title)}</div>
  <div class="contacts">{e(c.email)} · {e(c.phone)} ·
  <a href="{e(str(c.github))}">github.com/rafaumeu</a> ·
  <a href="{e(str(c.linkedin))}">LinkedIn</a></div>
</div>
<div class="meta-bar">{meta}</div>
<div class="body">
  <div class="recipient">
    <strong>Hiring Team{f' — {e(jd.company)}' if jd else ''}</strong>
    <span class="re">{re_line}</span>
  </div>
  <p>Olá,</p>
  {ps}
  <div class="closing">
    <div>
      <div class="sign-name">{e(profile.name)}</div>
      <div class="sign-sub">{e(profile.headline or profile.title)}</div>
    </div>
    <div class="cta-tag">{e(c.phone)}</div>
  </div>
</div>
<div class="footer">
  <a href="{e(str(c.github))}">github.com/rafaumeu</a> ·
  <a href="{e(str(c.linkedin))}">LinkedIn</a> ·
  <a href="{e(str(c.portfolio))}">Portfólio</a> · {e(c.email)}
</div>
</body></html>"""
