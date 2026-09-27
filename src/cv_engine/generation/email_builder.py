"""cv_engine.generation.email_builder — email de candidatura em HTML.

Template unificado premium (amber+dark): mesma identidade visual do CV
e da carta. Tabelas aninhadas (compatível com Gmail/Outlook).
Regra crítica: subject = título EXATO da vaga (vagas BR exigem).
"""
from __future__ import annotations

import re
from html import escape
from typing import List, Optional

from cv_engine.core.models import JobDescription, Profile
from cv_engine.generation.cover_letter import CoverLetter

DARK = "#111827"
ACCENT = "#f59e0b"
AMBER_BG = "#fef3c7"
GREY_BG = "#f9fafb"
BORDER = "#e5e7eb"
TXT = "#1f2937"
MUTED = "#6b7280"


def _whatsapp_link(phone: str, jd: JobDescription) -> str:
    """wa.me com mensagem pré-preenchida — recruiter clica e já abre conversa."""
    digits = re.sub(r"\D", "", phone)
    if not digits.startswith("55"):
        digits = "55" + digits
    msg = f"Olá, recebi seu currículo para a vaga de {jd.title} e gostaria de conversar."
    return f"https://wa.me/{digits}?text={escape(msg)}"


def build_email(profile: Profile, jd: JobDescription,
                cover_letter: Optional[CoverLetter] = None,
                attachments: Optional[List[str]] = None) -> dict:
    """Retorna {subject, html, text, attachments}."""
    subject = jd.title  # EXATO — nunca parafrasear

    c = profile.contact
    cl_html = ""
    if cover_letter:
        cl_ps = "".join(
            f'<p style="margin:0 0 14px;color:{TXT};line-height:1.6;">{escape(p)}</p>'
            for p in cover_letter.paragraphs)
        cl_html = cl_ps

    att_names = attachments or ["Rafael-Dias-Zendron-CV.pdf", "cover-letter.pdf"]
    att_html = "".join(
        f'<span style="display:inline-block;background:{GREY_BG};border:1px solid {BORDER};'
        f'border-radius:6px;padding:6px 12px;margin:4px 6px 0 0;font-size:12px;color:{TXT}">'
        f'📎 {escape(a)}</span>'
        for a in att_names)

    first = escape(profile.name.split(" ")[0])
    last = escape(profile.name.split(" ")[-1])
    wa = _whatsapp_link(c.phone, jd)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f3f4f6;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;border-radius:8px;overflow:hidden;border:1px solid {BORDER};">

  <!-- header dark com nome + headline (idêntico ao CV) -->
  <tr><td style="background:{DARK};padding:26px 36px 18px;border-bottom:4px solid {ACCENT};">
    <h1 style="color:#fff;font-size:22px;margin:0;letter-spacing:0.5px;">{first} <span style="color:{ACCENT};">{last}</span></h1>
    <p style="color:{ACCENT};font-size:12px;font-weight:bold;margin:4px 0 0;">{escape(profile.headline or profile.title)}</p>
    <p style="color:#9ca3af;font-size:11px;margin:8px 0 0;">Candidatura: {escape(jd.title)} @ {escape(jd.company)}</p>
  </td></tr>

  <!-- corpo -->
  <tr><td style="background:#fff;padding:28px 36px;">
    <p style="margin:0 0 16px;font-size:14px;color:{TXT};">
      Ao time de Recrutamento da <strong>{escape(jd.company)}</strong>,
    </p>
    {cl_html if cl_html else f'<p style="margin:0 0 16px;font-size:14px;color:{TXT};line-height:1.6;">Tenho interesse na vaga de <strong>{escape(jd.title)}</strong> e acredito que posso contribuir com o time com uma base sólida em desenvolvimento web e organização de código.</p>'}

    <!-- anexos -->
    <div style="margin:20px 0;">{att_html}</div>

    <!-- CTA WhatsApp pré-preenchido -->
    <table width="100%" cellpadding="0" cellspacing="0" style="background:{DARK};border-radius:6px;">
      <tr><td style="padding:20px 24px;text-align:center;">
        <p style="margin:0 0 12px;font-size:12px;color:#9ca3af;">
          Fico à disposição para conversar sobre a vaga.
        </p>
        <a href="{wa}" style="display:inline-block;background:{ACCENT};color:{DARK};
           padding:11px 26px;border-radius:6px;font-size:12px;font-weight:bold;text-decoration:none;">
          → FALAR PELO WHATSAPP</a>
      </td></tr>
    </table>
  </td></tr>

  <!-- footer dark -->
  <tr><td style="background:{DARK};padding:14px 36px;font-size:11px;color:#9ca3af;">
    <a href="{escape(str(c.github))}" style="color:#d1d5db;text-decoration:none;">github.com/rafaumeu</a> ·
    <a href="{escape(str(c.linkedin))}" style="color:#d1d5db;text-decoration:none;">LinkedIn</a> ·
    <a href="{escape(str(c.portfolio))}" style="color:#d1d5db;text-decoration:none;">Portfólio</a>
    · {escape(c.email)} · {escape(c.phone)}
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""

    # text fallback (clientes sem HTML)
    cl_text = "\n\n".join(cover_letter.paragraphs) if cover_letter else ""
    text = f"{profile.name} — {jd.title}\n\n{cl_text}\n\n{c.email} | {c.phone}\n{c.github}"

    return {"subject": subject, "html": html, "text": text, "attachments": att_names}
