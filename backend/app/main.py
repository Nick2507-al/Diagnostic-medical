"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .db import SessionLocal
from .models import User
from .routers import analyses, auth, chat
from .security import hash_password
from .services.ai import AIError

settings = get_settings()
logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("mediai")

MAX_BODY_BYTES = 60 * 1024 * 1024  # 5 files x 10 MB + form data


def ensure_default_user() -> None:
    if not (settings.default_user_email and settings.default_user_password):
        return
    email = settings.default_user_email.lower()
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)) is None:
            db.add(User(
                email=email,
                password_hash=hash_password(settings.default_user_password.get_secret_value()),
                full_name=settings.default_user_name,
                role="admin",
            ))
            db.commit()
            log.info("Default account created")


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_default_user()
    analyses.fail_stale_analyses()
    yield


app = FastAPI(
    title="MediAI API",
    version="2.0.0",
    lifespan=lifespan,
    # Interactive docs only outside production: they enumerate every route.
    docs_url=None if settings.is_production else "/api/docs",
    redoc_url=None,
    openapi_url=None if settings.is_production else "/api/openapi.json",
)

if settings.origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    length = request.headers.get("content-length")
    if length and (not length.isdigit() or int(length) > MAX_BODY_BYTES):
        return JSONResponse({"detail": "Requête trop volumineuse"}, status_code=status.HTTP_413_CONTENT_TOO_LARGE)
    response = await call_next(request)
    h = response.headers
    h["X-Content-Type-Options"] = "nosniff"
    h["X-Frame-Options"] = "DENY"
    h["Referrer-Policy"] = "no-referrer"
    h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    h["Cross-Origin-Opener-Policy"] = "same-origin"
    if not request.url.path.startswith("/api/docs"):
        h["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    if request.url.path.startswith("/api/") and "cache-control" not in h:
        h["Cache-Control"] = "no-store"  # medical data must not sit in shared caches
    if settings.cookie_secure:
        h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(AIError)
async def ai_error(_: Request, exc: AIError):
    return JSONResponse({"detail": str(exc)}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    # Never echo submitted values back (they may contain patient data or passwords).
    errors = [{"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
    return JSONResponse({"detail": errors}, status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Erreur interne du serveur"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/api/health", tags=["health"])
def health():
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ok", "ai_configured": settings.anthropic_api_key is not None}


app.include_router(auth.router)
app.include_router(analyses.router)
app.include_router(chat.router)
