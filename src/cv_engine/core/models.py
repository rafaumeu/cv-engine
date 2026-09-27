"""cv_engine.core.models — canonical schemas (source of truth).

Todos os geradores e parsers usam estes modelos. Dados sensíveis
vêm exclusivamente de data/profile-rafael-zendron.json (verificado).
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator


def _parse_ym(v: Any) -> Any:
    """Aceita 'YYYY-MM' (2024-07) além de ISO completo."""
    if isinstance(v, str) and len(v) == 7 and v[4] == "-":
        return f"{v}-01"
    return v


class Contact(BaseModel):
    email: EmailStr
    phone: str
    location: str
    github: Optional[HttpUrl] = None
    linkedin: Optional[HttpUrl] = None
    portfolio: Optional[HttpUrl] = None
    twitter: Optional[str] = None
    availability: Optional[str] = None  # ex: "Disponível para remoto full-time"


class Experience(BaseModel):
    company: str
    role: str
    period: str
    start: Optional[date] = None
    end: Optional[date] = None  # None = presente
    is_tech: bool = True
    description: str = ""
    achievements: List[str] = Field(default_factory=list)

    _v_start = field_validator("start", mode="before")(_parse_ym)
    _v_end = field_validator("end", mode="before")(_parse_ym)

    @property
    def is_current(self) -> bool:
        return self.end is None


class Project(BaseModel):
    name: str
    description: str
    result: str  # métrica mensurável — OBRIGATÓRIO (regra recruiter)
    technologies: List[str] = Field(default_factory=list)
    url: Optional[HttpUrl] = None
    featured: bool = True  # False = vira 1 linha em 'Outros projetos'


class Education(BaseModel):
    institution: str
    course: str
    status: str


class Certification(BaseModel):
    name: str
    issuer: str
    hours: Optional[int] = None

    def render(self) -> str:
        hours = f" ({self.hours}h)" if self.hours else ""
        return f"{self.name}{hours} — {self.issuer}"


class Profile(BaseModel):
    """Perfil canônico — carregado de data/profile-*.json."""

    name: str
    title: str
    seniority: str
    contact: Contact
    summary: str
    experience: List[Experience]
    projects: List[Project]
    education: List[Education]
    certifications: List[Certification]
    stack_categories: Dict[str, List[str]]
    soft_skills: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    honesty_rules: str = ""
    headline: str = ""
    complementary_education: List[Dict[str, str]] = Field(default_factory=list)
    certifications_footnote: str = ""
    other_projects_line: str = ""
    verified_facts: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_json_file(cls, path: str) -> "Profile":
        import json

        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        data = {k: v for k, v in raw.items() if not k.startswith("_")}
        data["summary"] = data.get("summary_options", [None])[0] or ""
        data.pop("summary_options", None)
        data.pop("star_stories", None)
        data.pop("preferred_contract", None)
        return cls(**data)


# ── Job & Matching ────────────────────────────────────────────────────


class JobDescription(BaseModel):
    id: str
    title: str
    company: str
    description: str
    requirements: List[str] = Field(default_factory=list)
    preferred: List[str] = Field(default_factory=list)
    stack: List[str] = Field(default_factory=list)
    location: str = ""
    remote: bool = False
    source_url: Optional[HttpUrl] = None
    posted_date: Optional[date] = None


class MatchResult(BaseModel):
    cv_id: str
    jd_id: str
    overall_score: float = Field(ge=0, le=100)
    skill_match: Dict[str, float]
    missing_skills: List[str]
    strong_skills: List[str]
    keyword_coverage: float = Field(ge=0, le=100)
    semantic_similarity: float = Field(ge=0, le=1)
    recommendations: List[str] = Field(default_factory=list)


# ── ATS ───────────────────────────────────────────────────────────────

ATS_VENDORS = ("greenhouse", "lever", "workday", "icims", "gupy", "generic")


class ATSReport(BaseModel):
    vendor: str
    parseable: bool
    score: float = Field(ge=0, le=100)
    field_scores: Dict[str, float]
    issues: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class GenerationResult(BaseModel):
    filename: str
    template: str
    bytes_size: int
    generated_at: datetime
    sha256: str
    ats_report: Optional[ATSReport] = None
