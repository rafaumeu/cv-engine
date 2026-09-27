#!/usr/bin/env python3
"""cv-engine CLI — uma vaga → set completo de candidatura.

Uso:
  python3 scripts/apply_kit.py --jd vaga.json --out /tmp/kit-mpan
  python3 scripts/apply_kit.py --demo   # usa vaga exemplo

Gera:
  cv-ats.html / cv-ats.pdf     — CV 100% parseável
  cover-letter.html            — carta 3 parágrafos
  email.html / email.txt       — email pronto pra enviar
  match-report.json            — score + recomendações + meta SHA-256
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))

from cv_engine.core.dossier import Verdict, build_dossier  # noqa: E402
from cv_engine.core.models import JobDescription, Profile  # noqa: E402
from cv_engine.generation.ats_builder import build_ats_cv, generation_meta  # noqa: E402
from cv_engine.generation.cover_letter import build_cover_letter, render_html  # noqa: E402
from cv_engine.generation.email_builder import build_email  # noqa: E402
from cv_engine.generation.premium_builder import build_premium_cv  # noqa: E402
from cv_engine.matching.matcher import match  # noqa: E402

DEMO_JD = {
    "id": "demo-001", "title": "Desenvolvedor Full Stack", "company": "Exemplo Ltda",
    "description": "Dev full stack para produtos digitais.",
    "requirements": ["React e TypeScript", "APIs REST com Node.js", "Testes automatizados"],
    "stack": ["React", "TypeScript", "Node.js", "PostgreSQL"],
    "location": "São Paulo, SP", "remote": True,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jd", help="JSON com a vaga")
    ap.add_argument("--out", default="/tmp/cv-engine-kit")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--spontaneous", action="store_true",
                    help="candidatura espontânea — carta não presume vaga aberta")
    args = ap.parse_args()

    if args.demo:
        jd_data = DEMO_JD
    elif args.jd:
        jd_data = json.loads(Path(args.jd).read_text())
    else:
        ap.error("--jd ou --demo")

    jd = JobDescription(**jd_data)
    profile = Profile.from_json_file(str(BASE / "data" / "profile-rafael-zendron.json"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # 0. DOSSIÊ DE FIT — veredito incisivo ANTES de qualquer material
    d = build_dossier(profile, jd)
    print(f"{'='*60}\nDOSSIÊ: {jd.title} @ {jd.company}")
    print(f"{'='*60}")
    print(f"VEREDITO: {d.verdict.value} (confiança {d.confidence}%, score {d.match_score})")
    print("\nFORÇAS:")
    for s in d.selling_points:
        print(f"  ✓ {s}")
    if d.honest_gaps:
        print("\nGAPS HONESTOS:")
        for g in d.honest_gaps:
            print(f"  ✗ {g}")
    if d.prep_before_applying:
        print("\nANTES DE APLICAR:")
        for p in d.prep_before_applying:
            print(f"  → {p}")
    print(f"\nPITCH: {d.pitch_line}")
    print(f"NEGOCIAÇÃO: {d.salary_leverage}\n")

    (out / "dossier.json").write_text(
        json.dumps({"veredito": d.verdict.value, "confianca": d.confidence,
                    "score": d.match_score, "forcas": d.selling_points,
                    "gaps": d.honest_gaps, "prep": d.prep_before_applying,
                    "pitch": d.pitch_line, "alavancagem": d.salary_leverage},
                   indent=2, ensure_ascii=False))

    if d.verdict == Verdict.SKIP:
        print(">>> Dossiê salvo. Kit NÃO gerado — fit insuficiente, capital de candidatura preservado.")
        return 2

    # 1. Match (gate: só gera kit se score razoável)
    result = match(profile, jd)
    print(f"match {jd.company}: {result.overall_score}/100")
    for r in result.recommendations:
        print(f"  → {r}")
    if result.overall_score < 40:
        print("score baixo — kit NÃO gerado (aplicação desperdiçada)")
        return 2

    # 2. CV nas DUAS variantes: ATS-flat (portais) + Premium (email humano)
    html = build_ats_cv(profile, job_title=jd.title,
                        keywords=jd.stack + result.strong_skills[:3])
    cv_html_path = out / "cv-ats.html"
    cv_html_path.write_text(html, encoding="utf-8")

    premium_html = build_premium_cv(profile, job_title=jd.title,
                                    keywords=jd.stack + result.strong_skills[:3])
    premium_path = out / "cv-premium.html"
    premium_path.write_text(premium_html, encoding="utf-8")

    import subprocess
    pdf_path = out / "cv-ats.pdf"
    premium_pdf = out / "cv-premium.pdf"
    for html_src, pdf_out in [(cv_html_path, pdf_path), (premium_path, premium_pdf)]:
        subprocess.run(
            ["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
             "--no-pdf-header-footer", f"--print-to-pdf={pdf_out}", str(html_src)],
            capture_output=True, timeout=60)
    pdf_ok = pdf_path.exists() and premium_pdf.exists()

    # 3. Cover letter (HTML premium + PDF)
    letter = build_cover_letter(profile, jd, spontaneous=args.spontaneous)
    issues = letter.validate()
    if issues:
        print("AVISO carta:", issues)
    cl_html = render_html(letter, profile, jd=jd)
    cl_path = out / "cover-letter.html"
    cl_path.write_text(cl_html, encoding="utf-8")
    subprocess.run(
        ["google-chrome", "--headless", "--disable-gpu", "--no-sandbox",
         "--no-pdf-header-footer", f"--print-to-pdf={out / 'cover-letter.pdf'}", str(cl_path)],
        capture_output=True, timeout=60)

    # 4. Email
    email = build_email(profile, jd, cover_letter=letter,
    attachments=["cv-premium.pdf", "cover-letter.pdf"])
    (out / "email.html").write_text(email["html"], encoding="utf-8")
    (out / "email.txt").write_text(email["text"], encoding="utf-8")

    # 5. Relatório
    report = {
        "dossier": {"veredito": d.verdict.value, "confianca": d.confidence,
                    "pitch": d.pitch_line, "alavancagem": d.salary_leverage},
        "match": json.loads(result.model_dump_json()),
        "cover_letter": {"words": letter.word_count, "metrics": letter.metrics_cited,
                         "validation_issues": issues},
        "email_subject": email["subject"],
        "cv_sha256": generation_meta(html, "ats-flat", cv_html_path.name)["sha256"],
        "pdf_generated": pdf_ok,
    }
    (out / "match-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print(f"\nkit completo: {out}")
    for f in sorted(out.iterdir()):
        print(f"  {f.name} ({f.stat().st_size}b)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
