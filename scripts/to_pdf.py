#!/usr/bin/env python3
"""cv-engine/scripts/to_pdf.py — HTML → PDF via Chrome headless.

Chrome headless é o mesmo motor do Playwright (career-ops) e renderiza
@page A4 corretamente. Zero dependências Python extras.

Uso: python3 scripts/to_pdf.py input.html [output.pdf]
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

CHROME_CANDIDATES = ["google-chrome", "chromium", "chromium-browser", "chrome"]


def _find_chrome() -> str:
    for c in CHROME_CANDIDATES:
        path = shutil.which(c)
        if path:
            return path
    raise RuntimeError("Chrome/Chromium não encontrado — instale ou use weasyprint")


def html_to_pdf(html_path: str, pdf_path: str | None = None) -> Path:
    src = Path(html_path).resolve()
    if not src.exists():
        raise FileNotFoundError(src)
    out = Path(pdf_path) if pdf_path else src.with_suffix(".pdf")

    cmd = [
        _find_chrome(),
        "--headless", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer",
        "--print-to-pdf=" + str(out),
        str(src),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if not out.exists():
        raise RuntimeError(f"PDF não gerado: {result.stderr[-500:]}")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    pdf = html_to_pdf(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"PDF: {pdf} ({pdf.stat().st_size} bytes)")
