# cv-engine

Pipeline Python que gera kits de candidatura completos e auditáveis: CV ATS-optimized (HTML semântico + PDF), CV premium visual, cover letter e email — a partir de um profile JSON verificado e de uma job description.

- Dossiê de fit com veredito incisivo (APLICA / NÃO CANDIDATA) antes de gerar qualquer material
- Matcher vaga↔candidato (BM25 com stopwords PT/EN e word boundaries)
- Gate de qualidade: falha o build se detectar clichês, números inflados, keywords duplicadas ou vazamento do matcher no documento
- 50 testes de regressão (pytest)
- PDF via Chrome headless, validação de extração de texto com pymupdf

## Uso

    uv run --with "pydantic[email]" python scripts/apply_kit.py --jd vaga.json --out /tmp/kit

## Gauntlet loop

    python3 scripts/gauntlet_loop.py --jd vaga.json

Gera o CV, extrai o texto do PDF e envia a um LLM revisor via router OpenAI-compatible para análise crítica iterativa.

*Este repositório é o engine; o profile de dados é exemplo anonimizado.*
