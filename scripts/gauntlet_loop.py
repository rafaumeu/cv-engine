#!/usr/bin/env python3
"""cv-engine/scripts/gauntlet_loop.py — loop de perfeição do CV.

Ciclo: gera CV → extrai texto do PDF → envia ao LLM via 9router para
análise crítica (recrutador sênior) → parse do veredito → repete até
APROVADO ou max_iterações.

Uso: python3 scripts/gauntlet_loop.py --jd /tmp/jd-mpan.json --max-iter 4
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))

ROUTER = "http://100.124.203.116:20129/v1/chat/completions"
REVIEWER_MODEL = "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free"


def _router_key() -> str:
    import tomllib
    cfg = Path.home() / ".hermes" / "config.yaml"
    m = re.search(r"9router:\s*\n\s*api_key: (\S+)", cfg.read_text())
    return m.group(1) if m else ""


def ask_reviewer(cv_text: str, history: list[dict]) -> dict:
    """Pede análise de recrutador sênior ao LLM. Retorna {verdict, score, issues}."""
    prompt = f"""Você é um recrutador técnico sênior brasileiro especializado em curriculos de dev.
Analise este CV (texto extraído do PDF, na ordem real de leitura de um ATS):

---CV---
{cv_text}
---FIM---

Avalie como ATS + recrutador humano:
1. ORDEM DE LEITURA: as seções aparecem em sequência lógica (Resumo → Competências →
   Experiência → Projetos → Formação → Certificações)? Algum bloco interrompe outro
   no meio (ex: stack de um projeto separada da sua descrição)?
2. PAGINAÇÃO: há título órfão no fim de página? Página final quase vazia?
3. CONTEÚDO: números consistentes? afirmações defensáveis? keywords suficientes?
4. ESCRITA: clichês? repetições? tom correto para júnior/pleno inicial?

Responda EXATAMENTE neste formato JSON (sem markdown):
{{"verdict": "APROVADO" ou "AJUSTAR", "score": 0-10,
  "issues": ["problema 1", "problema 2", ...],
  "fixes": ["correção concreta 1", ...]}}
Seja exigente: só APROVADO se não houver problemas reais."""
    messages = history + [{"role": "user", "content": prompt}]
    body = json.dumps({
        "model": REVIEWER_MODEL, "messages": messages, "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(ROUTER, data=body, headers={
        "Authorization": f"Bearer {_router_key()}",
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode()
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300]
        raise RuntimeError(f"router {e.code}: {detail}") from e
    # router às vezes concatena 2 JSONs — usa apenas o primeiro objeto completo
    dec = json.JSONDecoder()
    resp, _ = dec.raw_decode(raw.strip())
    content = resp["choices"][0]["message"]["content"]
    m = re.search(r"\{[\s\S]*\}", content)
    return json.loads(m.group(0)) if m else {"verdict": "ERRO", "score": 0,
                                             "issues": [content[:500]], "fixes": []}


def pdf_to_text(pdf: Path) -> str:
    """Extração via subprocess uv (pymupdf não está no env base)."""
    out = subprocess.run(
        ["uv", "run", "--with", "pymupdf", "python", "-c",
         f"import pymupdf; d=pymupdf.open('{pdf}'); print(''.join(p.get_text() for p in d))"],
        capture_output=True, text=True, timeout=120)
    return out.stdout


def generate_kit(out: Path, jd_path: str) -> None:
    subprocess.run([sys.executable, str(BASE / "scripts" / "apply_kit.py"),
                    "--jd", jd_path, "--out", str(out)], check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jd", required=True)
    ap.add_argument("--max-iter", type=int, default=4)
    ap.add_argument("--out", default="/tmp/gauntlet-cv")
    args = ap.parse_args()
    out = Path(args.out)

    history: list[dict] = []
    last_issues: list[str] = []

    for i in range(1, args.max_iter + 1):
        print(f"\n{'='*60}\nGAUNTLET RODADA {i}/{args.max_iter}\n{'='*60}")
        try:
            generate_kit(out, args.jd)
        except ValueError as e:
            print(f"gate de qualidade bloqueou: {e}")
            last_issues = [str(e)]
            continue

        cv_text = pdf_to_text(out / "cv-ats.pdf")
        print(f"CV: {len(cv_text)} chars extraidos. Enviando ao reviewer ({REVIEWER_MODEL})...")
        verdict = ask_reviewer(cv_text, history)
        print(f"\nVEREDITO: {verdict['verdict']} | score {verdict.get('score')}/10")
        for iss in verdict.get("issues", []):
            print(f"  ✗ {iss}")
        for fx in verdict.get("fixes", []):
            print(f"  → {fx}")

        if verdict["verdict"] == "APROVADO":
            print("\n✅ APROVADO pelo reviewer. Salvando memória da rodada.")
            (out / "gauntlet-verdict.json").write_text(
                json.dumps(verdict, indent=2, ensure_ascii=False))
            return 0

        history.append({"role": "assistant",
                        "content": json.dumps(verdict, ensure_ascii=False)})
        last_issues = verdict.get("fixes", verdict.get("issues", []))
        print("\n(!) Aplicar correções e rodar novamente.")

    print(f"\n✗ Máximo de rodadas atingido. Últimas pendências:\n" +
          "\n".join(f"  - {x}" for x in last_issues))
    return 1


if __name__ == "__main__":
    sys.exit(main())
