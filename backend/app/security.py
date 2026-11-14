"""Password hashing, server-side sessions, CSRF protection and the current-user dependency."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import User, UserSession

_hasher = PasswordHasher()  # argon2id with library defaults (OWASP-compliant parameters)
# Pre-computed hash used to keep login timing identical whether or not the account exists.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "x-csrf-token"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user: User, response: Response, user_agent: str | None) -> UserSession:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    sess = UserSession(
        user_id=user.id,
        token_hash=_token_hash(token),
        csrf_token=csrf,
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
        user_agent=(user_agent or "")[:300],
    )
    db.add(sess)
    # Opportunistic cleanup of this user's expired sessions.
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.expires_at < now))
    db.commit()
    max_age = settings.session_ttl_hours * 3600
    response.set_cookie(
        settings.session_cookie_name, token, max_age=max_age, httponly=True,
        secure=settings.cookie_secure, samesite="lax", path="/",
    )
    # Readable by the frontend JS so it can echo it in the X-CSRF-Token header (double submit).
    response.set_cookie(
        settings.csrf_cookie_name, csrf, max_age=max_age, httponly=False,
        secure=settings.cookie_secure, samesite="lax", path="/",
    )
    return sess


def clear_session_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


def _load_session(request: Request, db: Session) -> UserSession | None:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token or len(token) > 200:
        return None
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == _token_hash(token)))
    if sess is None or sess.expires_at <= datetime.now(timezone.utc):
        return None
    return sess


def get_current_session(request: Request, db: Session = Depends(get_db)) -> UserSession:
    sess = _load_session(request, db)
    if sess is None or not sess.user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise")
    if request.method not in SAFE_METHODS:
        sent = request.headers.get(CSRF_HEADER, "")
        if not sent or not hmac.compare_digest(sent, sess.csrf_token):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Jeton CSRF invalide")
    return sess


def get_current_user(sess: UserSession = Depends(get_current_session)) -> User:
    return sess.user
