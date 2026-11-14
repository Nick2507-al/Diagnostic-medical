"""Analyses: create (with documents), list/search history, read, retry, delete."""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, selectinload, undefer

from ..config import get_settings
from ..db import SessionLocal, get_db
from ..models import Analysis, AnalysisFile, Conversation, User
from ..ratelimit import limiter
from ..schemas import AnalysisIn, AnalysisOut, AnalysisPage, StatsOut
from ..security import get_current_user
from ..services.ai import AIError, AIProvider, CaseContext, format_patient, get_ai
from ..services.documents import DocumentError, content_blocks, parse_upload

router = APIRouter(prefix="/api", tags=["analyses"])
log = logging.getLogger("mediai.analyses")


def owned_analysis(db: Session, user: User, analysis_id: uuid.UUID, *, with_content: bool = False) -> Analysis:
    opts = [selectinload(Analysis.files)]
    if with_content:
        opts = [selectinload(Analysis.files).options(undefer(AnalysisFile.content))]
    a = db.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user.id).options(*opts))
    if a is None:  # same response whether it does not exist or belongs to someone else
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analyse introuvable")
    return a


def build_case(a: Analysis, include_report: bool) -> CaseContext:
    docs: list[dict] = []
    for f in a.files:
        docs.extend(content_blocks(f.filename, f.kind, f.media_type, f.content, f.extracted_text))
    return CaseContext(
        patient_text=format_patient(a.patient, a.symptoms, a.clinical_notes, a.title),
        documents=docs,
        report=a.result if include_report else None,
    )


def run_analysis(analysis_id: uuid.UUID, ai: AIProvider) -> None:
    """Background job: own DB session, never raises."""
    db = SessionLocal()
    try:
        a = db.scalar(
            select(Analysis).where(Analysis.id == analysis_id)
            .options(selectinload(Analysis.files).options(undefer(AnalysisFile.content)))
        )
        if a is None:
            return
        try:
            result = ai.analyze(build_case(a, include_report=False))
        except AIError as exc:
            a.status, a.error_message = "error", str(exc)[:500]
        except Exception:  # noqa: BLE001 - background job must record failure, not crash
            log.exception("analysis %s failed", analysis_id)
            a.status, a.error_message = "error", "Erreur interne pendant l'analyse."
        else:
            report = result.report
            a.result = report
            a.status = "done"
            a.error_message = None
            a.triage_level = report["triage"]["niveau"]
            a.top_diagnosis = (report["hypotheses"][0]["maladie"] if report["hypotheses"] else report["diagnostic_retenu"])[:300]
            a.model, a.input_tokens, a.output_tokens = result.model, result.input_tokens, result.output_tokens
        a.completed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def fail_stale_analyses() -> None:
    """Analyses left 'pending' by a server restart would otherwise spin forever."""
    with SessionLocal() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=20)
        db.execute(
            update(Analysis)
            .where(Analysis.status == "pending", Analysis.created_at < cutoff)
            .values(status="error", error_message="Analyse interrompue (redémarrage du serveur). Relancez-la.")
        )
        db.commit()


@router.post("/analyses", response_model=AnalysisOut, status_code=status.HTTP_202_ACCEPTED)
def create_analysis(  # sync: runs in the threadpool, so blocking DB/parsing work never stalls the event loop
    request: Request,
    background: BackgroundTasks,
    data: str = Form(..., max_length=40000),
    files: list[UploadFile] = File(default=[]),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai: AIProvider = Depends(get_ai),
):
    settings = get_settings()
    limiter.hit(f"analyses:{user.id}", settings.analyses_per_hour, 3600)
    try:
        body = AnalysisIn.model_validate(json.loads(data))
    except (json.JSONDecodeError, ValidationError) as exc:
        detail = exc.errors(include_url=False, include_input=False) if isinstance(exc, ValidationError) else "JSON invalide"
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail) from None
    if len(files) > settings.max_files_per_analysis:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Maximum {settings.max_files_per_analysis} fichiers")
    if not body.symptoms.strip() and not body.clinical_notes.strip() and not files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Décrivez les symptômes ou joignez un document")

    parsed = []
    for upload in files:
        raw = upload.file.read(settings.max_file_bytes + 1)
        try:
            parsed.append(parse_upload(upload.filename, raw))
        except DocumentError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from None

    title = body.title or (body.symptoms.strip().splitlines() or [parsed[0].filename if parsed else "Analyse"])[0]
    a = Analysis(
        user_id=user.id,
        title=title[:200],
        patient=body.patient.model_dump(exclude_none=True),
        symptoms=body.symptoms,
        clinical_notes=body.clinical_notes,
        status="pending",
    )
    for p in parsed:
        a.files.append(AnalysisFile(
            filename=p.filename, kind=p.kind, media_type=p.media_type, size_bytes=len(p.data),
            sha256=p.sha256, content=p.data, extracted_text=p.text,
        ))
    db.add(a)
    db.commit()
    background.add_task(run_analysis, a.id, ai)
    return a


@router.post("/analyses/{analysis_id}/retry", response_model=AnalysisOut, status_code=status.HTTP_202_ACCEPTED)
def retry_analysis(
    analysis_id: uuid.UUID,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai: AIProvider = Depends(get_ai),
):
    limiter.hit(f"analyses:{user.id}", get_settings().analyses_per_hour, 3600)
    a = owned_analysis(db, user, analysis_id)
    if a.status == "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Analyse déjà en cours")
    a.status, a.error_message, a.completed_at = "pending", None, None
    db.commit()
    background.add_task(run_analysis, a.id, ai)
    return a


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/analyses", response_model=AnalysisPage)
def list_analyses(
    q: str | None = Query(default=None, max_length=100),
    triage: str | None = Query(default=None, pattern="^(urgence_vitale|urgent|consultation_rapide|non_urgent)$"),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Analysis).where(Analysis.user_id == user.id)
    if q:
        pattern = f"%{_escape_like(q)}%"
        stmt = stmt.where(or_(
            Analysis.title.ilike(pattern, escape="\\"),
            Analysis.symptoms.ilike(pattern, escape="\\"),
            Analysis.top_diagnosis.ilike(pattern, escape="\\"),
        ))
    if triage:
        stmt = stmt.where(Analysis.triage_level == triage)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Analysis.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return AnalysisPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return owned_analysis(db, user, analysis_id)


@router.delete("/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(owned_analysis(db, user, analysis_id))
    db.commit()


@router.get("/stats", response_model=StatsOut)
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mine = Analysis.user_id == user.id
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    by_triage = dict(db.execute(
        select(Analysis.triage_level, func.count()).where(mine, Analysis.triage_level.is_not(None))
        .group_by(Analysis.triage_level)
    ).all())
    top = db.execute(
        select(Analysis.top_diagnosis, func.count().label("n")).where(mine, Analysis.top_diagnosis.is_not(None))
        .group_by(Analysis.top_diagnosis).order_by(func.count().desc()).limit(5)
    ).all()
    return StatsOut(
        total_analyses=db.scalar(select(func.count()).where(mine)) or 0,
        analyses_this_month=db.scalar(select(func.count()).where(mine, Analysis.created_at >= month_start)) or 0,
        by_triage=by_triage,
        top_diagnoses=[{"diagnostic": d, "nombre": n} for d, n in top],
        conversations=db.scalar(select(func.count()).select_from(Conversation).where(Conversation.user_id == user.id)) or 0,
    )
