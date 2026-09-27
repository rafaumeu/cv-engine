---
name: cv-engine
category: recruitment
description: "Optimized CV engine for career-ops (parse, match, generate)."
platforms: [linux, macos, windows]
---

# cv-engine — Recruitment Engineering Toolkit

**Mission**: Build the *engine* that powers career-ops (HireMe Agent) — CV generation, ATS parsing, semantic matching, cover letters, scraping, LGPD compliance, interview prep. All measurable, all tested, all production-ready.

---

## Architecture

```
career-ops (TypeScript/Next.js)          cv-engine (Python/FastAPI)
       │                                        │
       │  HTTP/JSON (internal, typed)          │
       ▼                                        ▼
┌─────────────────────┐              ┌─────────────────────┐
│ API Gateway         │◄────────────►│ FastAPI             │
│ - Auth              │   /parse     │ - Core              │
│ - Rate limit        │   /match     │   • Parser          │
│ - Queue             │   /generate  │   • Matcher         │
│ - Webhooks          │   /scrape    │   • Generator       │
└─────────────────────┘   /validate  │   • Scraper         │
                           /coach     │   • Compliance      │
                                      │   • Interview       │
                                      └─────────────────────┘
```

**Contract**: OpenAPI 3.1 → Pydantic ↔ Zod compatible. Versioned at `/api/v1/`.

---

## Core Modules

### 1. `core/models.py` — Pydantic Schemas (SOURCE OF TRUTH)

```python
# src/cv_engine/core/models.py
from __future__ import annotations
from datetime import date
from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, EmailStr, HttpUrl, field_validator


class Contact(BaseModel):
    email: EmailStr
    phone: str = Field(pattern=r'^\+?[1-9]\d{1,14}$')
    github: Optional[HttpUrl] = None
    linkedin: Optional[HttpUrl] = None
    portfolio: Optional[HttpUrl] = None
    location: str  # "Jaú, SP, Brazil"


class Experience(BaseModel):
    company: str
    role: str
    start_date: date
    end_date: Optional[date] = None  # None = present
    description: str
    achievements: List[str] = Field(default_factory=list)
    stack: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)  # {"tests": 1900, "coverage": 100}

    @property
    def period_str(self) -> str:
        start = self.start_date.strftime('%b %Y')
        end = self.end_date.strftime('%b %Y') if self.end_date else 'Presente'
        return f'{start} – {end}'


class Project(BaseModel):
    name: str
    description: str
    stack: List[str]
    github_url: Optional[HttpUrl] = None
    deploy_url: Optional[HttpUrl] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    is_private: bool = False


class Education(BaseModel):
    institution: str
    degree: str
    field: str
    start_date: date
    end_date: Optional[date] = None
    gpa: Optional[float] = None


class Certification(BaseModel):
    name: str
    issuer: str
    date: date
    url: Optional[HttpUrl] = None
    hours: Optional[int] = None


class SkillCategory(str, Enum):
    LANGUAGES = "Linguagens"
    FRAMEWORKS = "Frameworks"
    DATABASES = "Banco de dados"
    TOOLS = "Ferramentas"
    CLOUD = "Cloud"
    ARCHITECTURE = "Arquiteturas"
    TESTING = "Testes"
    OTHER = "Outros"


class Skill(BaseModel):
    name: str
    category: SkillCategory
    proficiency: int = Field(ge=1, le=5)  # 1-5
    years: Optional[float] = None
    last_used: Optional[date] = None


class StructuredCV(BaseModel):
    """Canonical CV representation — all generators/parsers use this."""
    name: str
    title: str  # exact job title target
    contact: Contact
    summary: str  # 2-3 lines, metrics, no clichés
    experience: List[Experience]
    projects: List[Project]
    education: List[Education]
    certifications: List[Certification]
    skills: List[Skill]
    languages: List[str] = Field(default_factory=lambda: ["Português (Nativo)", "Inglês (Avançado)"])
    raw_text: Optional[str] = None  # original extracted text


class JobDescription(BaseModel):
    id: str
    title: str
    company: str
    description: str
    requirements: List[str]
    preferred: List[str] = Field(default_factory=list)
    stack: List[str] = Field(default_factory=list)
    location: str
    remote: bool = False
    salary_range: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    posted_date: Optional[date] = None


class MatchResult(BaseModel):
    cv_id: str
    jd_id: str
    overall_score: float = Field(ge=0, le=100)
    skill_match: Dict[str, float]  # skill -> 0-100
    missing_skills: List[str]
    strong_skills: List[str]
    experience_match: float = Field(ge=0, le=100)
    semantic_similarity: float = Field(ge=0, le=1)
    keyword_coverage: float = Field(ge=0, le=100)
    recommendations: List[str]


class ATSReport(BaseModel):
    """ATS parseability report for a generated CV."""
    vendor: Literal["greenhouse", "lever", "workday", "icims", "gupy", "generic"]
    parseable: bool
    field_scores: Dict[str, float]  # field -> 0-100
    issues: List[str]
    warnings: List[str]
    suggestions: List[str]
    raw_extracted: Dict[str, Any]  # what ATS actually extracts


class CoverLetterRequest(BaseModel):
    cv: StructuredCV
    jd: JobDescription
    tone: Literal["professional", "enthusiastic", "direct"] = "professional"
    custom_hook: Optional[str] = None  # company-specific connection


class CoverLetter(BaseModel):
    content: str  # markdown
    html: str     # renderizado
    word_count: int
    paragraphs: int
    metrics_cited: List[str]


class EmailRequest(BaseModel):
    to: EmailStr
    subject: str  # MUST match job title exactly
    cv: StructuredCV
    jd: JobDescription
    cover_letter: Optional[CoverLetter] = None
    template: Literal["default", "minimal", "referral"] = "default"


class EmailDraft(BaseModel):
    subject: str
    html: str
    text: str
    attachments: List[str]  # filenames


class STARStory(BaseModel):
    id: str
    situation: str
    task: str
    action: str
    result: str  # MUST have metrics
    competencies: List[str]
    tags: List[str] = Field(default_factory=list)


class InterviewRubric(BaseModel):
    competency: str
    weight: float = Field(ge=0, le=1)
    bars: Dict[int, str]  # 1-5 -> behavioral anchor
    must_have: bool = False


class InterviewScore(BaseModel):
    rubric: InterviewRubric
    score: int = Field(ge=1, le=5)
    evidence: str
    confidence: float = Field(ge=0, le=1)


class MockInterviewResult(BaseModel):
    overall_score: float
    competency_scores: List[InterviewScore]
    feedback: str
    star_stories_used: List[str]
    areas_to_improve: List[str]
```

---

### 2. `core/parser.py` — PDF/DOCX → StructuredCV

**Stack**: `pymupdf` (fitz) + `python-docx` + `spaCy` (NER custom) + `layoutlmv3` (layout) + regex fallback.

**Pipeline**:
```
PDF/DOCX → Text Extraction (pymupdf/docx)
    → Layout Analysis (layoutlmv3) → Section Detection
    → NER Extraction (spaCy custom: PERSON, ORG, DATE, SKILL, METRIC)
    → Regex Fallback (email, phone, URLs, dates)
    → StructuredCV Assembly + Validation
```

**Target**: ≥97% field accuracy on 200 real CVs (fixtures).

---

### 3. `core/validators.py` — ATS Rules per Vendor

| Vendor | Rules File | Key Checks |
|---|---|---|
| Greenhouse | `greenhouse.yaml` | h2 sections, time datetime, semantic HTML |
| Lever | `lever.yaml` | single-column, no tables, selectable text |
| Workday | `workday.yaml` | strict heading hierarchy, no headers/footers |
| iCIMS | `icims.yaml` | keyword density, standard section names |
| Gupy | `gupy.yaml` | PT-BR keywords, CPF/CNPJ detection, Brazilian date format |
| Generic | `generic.yaml` | baseline: text-selectable, single-column, h1/h2/h3 |

**Output**: `ATSReport` with field_scores, issues, suggestions.

---

### 4. `matching/` — Hybrid Matcher (Lexical + Semantic + LTR)

- **Lexical**: BM25 (rank-bm25) on skill/requirement tokens
- **Semantic**: bge-m3 / e5-mistral embeddings + faiss k-NN
- **LTR (optional)**: LightGBM LambdaMART trained on historical match→callback data
- **Output**: `MatchResult` with actionable recommendations

---

### 5. `generation/` — CV + Cover Letter + Email

| Template | Output | Use Case |
|---|---|---|
| `ats-flat.j2` | DOCX/PDF (single-column, semantic HTML) | ATS portals (Greenhouse, Lever, Gupy) |
| `premium.j2` | DOCX/PDF (amber+black, two-column visual) | Direct email, portfolio, print |
| `minimal.j2` | DOCX/PDF (clean, single-column) | Conservative parsers, fallback |

**Cover Letter**: llama.cpp local (7B instruct) + few-shot templates → 3 paragraphs, metrics, active closing.
**Email**: HTML wrapper (dark header, gradient CTA, signature) + plain text fallback.

---

### 6. `scraping/` — Resilient Job Scraping

- **scrapling** (HTTP-only) for: GitHub Issues, Gupy API, Nerdin, GeekHunter
- **playwright-stealth** for: LinkedIn, Indeed, Glassdoor, Programathor
- **Normalizer**: RawJob → `NormalizedJob` (Pydantic) with dedup by (company, title, url)

---

### 7. `compliance/` — LGPD Guard

- **spaCy NER custom** trained on Brazilian PII (CPF, RG, CNH, endereço, telefone, email)
- **Regex compiled** for patterns: `\d{3}\.\d{3}\.\d{3}-\d{2}` (CPF), etc.
- **Sanitizer**: Redact/tokenize before auto-apply.

---

### 8. `interview/` — STAR Bank + Coach

- **STARStory** bank (8-12 versatile stories, mapped to competencies)
- **BARS Rubric** per competency (1-5 anchors)
- **Mock Coach**: Simulates interviewer, scores via rubric, gives feedback

---

## API Endpoints (FastAPI)

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/parse` | PDF/DOCX → StructuredCV + ATSReport |
| POST | `/api/v1/match` | StructuredCV + JobDescription → MatchResult |
| POST | `/api/v1/generate/cv` | StructuredCV + template → DOCX/PDF bytes |
| POST | `/api/v1/generate/cover-letter` | CoverLetterRequest → CoverLetter |
| POST | `/api/v1/generate/email` | EmailRequest → EmailDraft |
| POST | `/api/v1/scrape` | Source config → List[NormalizedJob] |
| POST | `/api/v1/validate/ats` | CV bytes + vendor → ATSReport |
| POST | `/api/v1/compliance/sanitize` | StructuredCV → sanitized StructuredCV |
| POST | `/api/v1/coach/mock` | Competencies + STAR bank → MockInterviewResult |

---

## Metrics & Targets (Contract)

| Module | Metric | Target | Measurement |
|---|---|---|---|
| Parser | Field extraction accuracy | **≥97%** | 200 CVs fixtures, ground truth |
| Parser | ATS-flat parseability | **100%** | Real upload to Greenhouse/Lever/Gupy |
| Matcher | JD↔CV correlation (callback) | **r ≥ 0.75** | A/B test 500+ applications |
| Generator | ATS-flat parseability | **100%** | Same as parser |
| Generator | Visual parity (Premium) | **Pixel-perfect** | Playwright screenshot diff |
| Cover Letter | Recruiter response lift | **+40%** | UTM tracking + reply detection |
| Scraper | Jobs/day (blocked portals) | **≥500/day** | Cron metrics |
| LGPD Guard | False negative (PII leak) | **0** | Red team automated |
| Interview Coach | Mock→Real correlation | **r ≥ 0.8** | Longitudinal tracking |

---

## Installation & Usage (verified working)

Use `uv run --with` to pull transient deps into the run — the system python already has pydantic, and `pytest` is NOT in the Hermes venv (no module named pytest). Do NOT run `uv venv` interactively; it stalls waiting for consent in headless sessions.

```bash
cd ~/.hermes/skills/recruitment/cv-engine

# Run the full test suite (29 tests)
uv run --with pytest --with "pydantic[email]" python -m pytest tests/ -q --no-header

# Generate a full application kit from a job description JSON
uv run --with "pydantic[email]" python scripts/apply_kit.py --jd vaga.json --out /tmp/kit
uv run --with "pydantic[email]" python scripts/apply_kit.py --demo --out /tmp/kit-demo

# HTML → PDF (uses google-chrome headless; no weasyprint needed)
python3 scripts/to_pdf.py data/cv-rafael-zendron-ats.html

# Verify a PDF is ATS-extractable (all key fields present as text)
uv run --with pymupdf python -c "import pymupdf; print(''.join(p.get_text() for p in pymupdf.open('<pdf>')))"
```

Kit output per job: `cv-ats.html` + `cv-ats.pdf` (100% text-extractable), `cover-letter.html` (3 paragraphs, ≤350 words), `email.html`/`email.txt` (subject = exact job title), `match-report.json` (score + SHA-256 + recommendations). The CLI refuses to build a kit when match score < 40 — a low-score application is a wasted application.

---

## Integration with career-ops (TypeScript)

```typescript
// career-ops/src/lib/cv-engine-client.ts
import { z } from 'zod';

const CVEngineClient = {
  async parse(file: Buffer): Promise<StructuredCV> {
    const form = new FormData();
    form.append('file', new Blob([file]), 'cv.pdf');
    const res = await fetch('http://localhost:8080/api/v1/parse', {
      method: 'POST',
      body: form,
      headers: { 'Authorization': `Bearer ${process.env.CV_ENGINE_TOKEN}` }
    });
    return StructuredCVSchema.parse(await res.json());
  },
  // ... match, generate, scrape, validate, coach
};
```

---

## Development Workflow

1. **Spec first** — Update `SKILL.md` (this file) with new module/contract
2. **Test first** — Add fixture + test case in `tests/`
3. **Implement** — Code in `src/cv_engine/`
4. **Benchmark** — Run `benchmarks/run_bench.py`
5. **Verify** — `pytest` + `uv run ruff check` + `uv run mypy`
6. **Document** — Update README.md with usage examples

---

## Roadmap (Next Modules)

- [x] `core/models.py` — Pydantic v2 + validador YYYY-MM (13 testes)
- [x] `generation/ats_builder.py` — HTML semântico ATS-flat (título exato, keywords, sha256)
- [x] `generation/cover_letter.py` — 3 parágrafos, validador de clichês/350 palavras
- [x] `generation/email_builder.py` — dark header, CTA, subject = título exato
- [x] `matching/matcher.py` — BM25 + stopwords PT/EN, word boundaries (bug java/js corrigido)
- [x] `scripts/to_pdf.py` + `scripts/apply_kit.py` — CLI uma-vaga→kit-completo
- [x] `data/profile-rafael-zendron.json` — dados reais verificados (hireme-agent config.ts)
- [x] 29/29 testes verdes + PDF validado com pymupdf (100% texto extraível)
- [x] `generation/premium_builder.py` — variante visual amber+black 2 colunas (35 testes)
- [x] `apply_kit.py` gera kit completo: cv-ats + cv-premium + carta + email + relatório (8 arquivos)
- [x] Verificação geométrica de layout via pymupdf (header #111827 confirmado, 2 colunas ativas)
- [ ] `core/parser.py` — parse de PDFs de terceiros (pymupdf + NER)
- [ ] `scraping/`, `compliance/lgpd_guard`, `interview/coach`, FastAPI wrapper

---

## References

- `career-ops` skill: `/home/rafaelejosi/.hermes/skills/productivity/career-ops`
- ATS Audit: `career-ops/references/ats-audit.md`
- Recruitment Quality Framework: `career-ops/references/recruitment-quality-framework.md`
- BR Job Sources: `career-ops/references/br-job-sources.md`
- Tavily Research (2024-2025): ATS parsing, interview frameworks, Brazil LGPD

---

*Generated by Hermes Agent — Specialist mode: Recruitment Engineering*
