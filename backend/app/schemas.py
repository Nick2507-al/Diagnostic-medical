"""API request/response schemas and the structured diagnosis report produced by the AI."""
import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ───────────────────────────── Auth ─────────────────────────────

PASSWORD_RULES = "au moins 10 caractères, avec au moins une lettre et un chiffre"


class RegisterIn(Strict):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    specialty: str | None = Field(default=None, max_length=120)

    @field_validator("password")
    @classmethod
    def strong(cls, v: str) -> str:
        if not (re.search(r"[A-Za-zÀ-ÿ]", v) and re.search(r"\d", v)):
            raise ValueError(f"Mot de passe trop faible : {PASSWORD_RULES}")
        return v

    @field_validator("full_name", "specialty")
    @classmethod
    def no_control_chars(cls, v: str | None) -> str | None:
        if v is not None and re.search(r"[\x00-\x1f<>]", v):
            raise ValueError("Caractères non autorisés")
        return v


class LoginIn(Strict):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    specialty: str | None
    role: str
    created_at: datetime


# ─────────────────────────── Patient input ──────────────────────────

class PatientContext(Strict):
    age_years: float | None = Field(default=None, ge=0, le=130)
    sex: Literal["homme", "femme", "autre", "inconnu"] = "inconnu"
    weight_kg: float | None = Field(default=None, gt=0, le=400)
    pregnant: Literal["oui", "non", "inconnu", "sans_objet"] = "inconnu"
    pregnancy_weeks: int | None = Field(default=None, ge=0, le=45)
    country: str | None = Field(default=None, max_length=80)
    region: str | None = Field(default=None, max_length=120)
    setting: Literal["communautaire", "centre_de_sante", "hopital_district", "hopital_reference", "inconnu"] = "inconnu"
    comorbidities: str | None = Field(default=None, max_length=1000)
    allergies: str | None = Field(default=None, max_length=500)
    current_medications: str | None = Field(default=None, max_length=1000)
    hiv_status: Literal["positif", "negatif", "inconnu"] = "inconnu"
    vaccination: str | None = Field(default=None, max_length=500)
    recent_travel: str | None = Field(default=None, max_length=500)
    temperature_c: float | None = Field(default=None, ge=25, le=45)
    heart_rate: int | None = Field(default=None, ge=10, le=300)
    respiratory_rate: int | None = Field(default=None, ge=2, le=120)
    systolic_bp: int | None = Field(default=None, ge=30, le=300)
    diastolic_bp: int | None = Field(default=None, ge=10, le=200)
    spo2: int | None = Field(default=None, ge=30, le=100)
    glycemia_g_l: float | None = Field(default=None, ge=0, le=15)


class AnalysisIn(Strict):
    title: str | None = Field(default=None, max_length=200)
    symptoms: str = Field(default="", max_length=8000)
    clinical_notes: str = Field(default="", max_length=20000)
    patient: PatientContext = Field(default_factory=PatientContext)


# ─────────────────────── AI structured report ───────────────────────
# Kept free of numeric/length constraints: the structured-output schema does not support them.
# Bounds are enforced after parsing (see services/ai.py: normalise_report).

TriageLevel = Literal["urgence_vitale", "urgent", "consultation_rapide", "non_urgent"]


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Hypothesis(Report):
    maladie: str = Field(description="Nom de la maladie en français")
    code_cim10: str = Field(description="Code CIM-10 le plus spécifique possible, ou chaîne vide")
    probabilite: int = Field(description="Probabilité estimée en pourcentage (0-100)")
    justification: str = Field(description="Raisonnement clinique expliquant cette probabilité")
    elements_pour: list[str]
    elements_contre: list[str]
    examens_de_confirmation: list[str] = Field(description="Examens permettant de confirmer ou d'exclure, en priorisant ceux disponibles localement (TDR, microscopie…)")


class Triage(Report):
    niveau: TriageLevel
    justification: str


class Decision(Report):
    conduite_a_tenir: str = Field(description="Décision clinique recommandée (ex. hospitalisation, traitement ambulatoire, référence)")
    justification: str
    examens_prioritaires: list[str]
    criteres_de_reference: list[str] = Field(description="Situations imposant un transfert vers un niveau supérieur")


class Medication(Report):
    medicament: str = Field(description="DCI du médicament")
    posologie: str = Field(description="Dose adaptée au patient (poids/âge/grossesse), avec unité")
    voie: str
    frequence: str
    duree: str
    remarques: str = Field(description="Précautions, adaptation rénale/hépatique, interactions, disponibilité LME OMS")


class TreatmentPlan(Report):
    pour_diagnostic: str = Field(description="Diagnostic visé par ce plan de traitement")
    premiere_intention: list[Medication]
    alternatives: list[Medication]
    traitement_symptomatique: list[Medication]
    mesures_non_medicamenteuses: list[str]
    contre_indications_et_precautions: list[str]
    surveillance: list[str] = Field(description="Paramètres à surveiller et critères d'évolution")
    suivi: str


class DiagnosisReport(Report):
    synthese_clinique: str
    donnees_manquantes: list[str] = Field(description="Informations dont l'absence limite la précision du diagnostic")
    triage: Triage
    hypotheses: list[Hypothesis] = Field(description="Diagnostics différentiels classés par probabilité décroissante; la somme des probabilités vaut 100")
    diagnostic_retenu: str
    signes_d_alarme: list[str]
    decision: Decision
    traitement: TreatmentPlan
    prevention: list[str]
    references: list[str] = Field(description="Recommandations utilisées (OMS, protocoles nationaux…), avec année")
    niveau_de_confiance: Literal["eleve", "modere", "faible"]
    avertissement: str


# ───────────────────────────── Outputs ─────────────────────────────

class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    filename: str
    kind: str
    media_type: str
    size_bytes: int
    created_at: datetime


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    status: str
    triage_level: str | None
    top_diagnosis: str | None
    created_at: datetime
    completed_at: datetime | None


class AnalysisOut(AnalysisSummary):
    patient: dict
    symptoms: str
    clinical_notes: str
    result: dict | None
    error_message: str | None
    model: str | None
    files: list[FileOut]


class AnalysisPage(BaseModel):
    items: list[AnalysisSummary]
    total: int
    page: int
    page_size: int


class ConversationIn(Strict):
    analysis_id: uuid.UUID | None = None
    title: str | None = Field(default=None, max_length=200)


class MessageIn(Strict):
    content: str = Field(min_length=1, max_length=8000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    analysis_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ConversationOut(ConversationSummary):
    messages: list[MessageOut]


class StatsOut(BaseModel):
    total_analyses: int
    analyses_this_month: int
    by_triage: dict[str, int]
    top_diagnoses: list[dict]
    conversations: int
