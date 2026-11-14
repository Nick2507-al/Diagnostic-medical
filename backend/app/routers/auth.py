"""Registration, login, logout, current user, account deletion."""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import User, UserSession
from ..ratelimit import client_ip, limiter
from ..schemas import LoginIn, RegisterIn, UserOut
from ..security import (
    clear_session_cookies,
    create_session,
    get_current_session,
    get_current_user,
    hash_password,
    needs_rehash,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
audit = logging.getLogger("mediai.audit")

INVALID_CREDENTIALS = "Email ou mot de passe incorrect"


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    limiter.hit(f"register:{client_ip(request)}", get_settings().register_per_hour, 3600)
    email = body.email.lower()
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        specialty=body.specialty or None,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet email") from None
    audit.info("register user=%s ip=%s", user.id, client_ip(request))
    create_session(db, user, response, request.headers.get("user-agent"))
    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    ip = client_ip(request)
    email = body.email.lower()
    limiter.hit(f"login:{ip}", settings.login_attempts_per_15min, 900)
    limiter.hit(f"login-account:{email}", settings.login_attempts_per_15min, 900)

    user = db.scalar(select(User).where(User.email == email))
    now = datetime.now(timezone.utc)
    if user is not None and user.locked_until and user.locked_until > now:
        verify_password(None, body.password)  # constant-ish timing
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS)

    ok = verify_password(user.password_hash if user else None, body.password)
    if user is None or not ok or not user.is_active:
        if user is not None:
            user.failed_logins += 1
            if user.failed_logins >= settings.account_lockout_threshold:
                user.locked_until = now + timedelta(minutes=settings.account_lockout_minutes)
                user.failed_logins = 0
                audit.warning("lockout user=%s ip=%s", user.id, ip)
            db.commit()
        audit.info("login_failed ip=%s", ip)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, INVALID_CREDENTIALS)

    user.failed_logins = 0
    user.locked_until = None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    db.commit()
    audit.info("login user=%s ip=%s", user.id, ip)
    create_session(db, user, response, request.headers.get("user-agent"))
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, sess: UserSession = Depends(get_current_session), db: Session = Depends(get_db)):
    db.execute(delete(UserSession).where(UserSession.id == sess.id))
    db.commit()
    clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Right to erasure: removes the account and, by cascade, every analysis, file and conversation."""
    audit.info("account_deleted user=%s", user.id)
    db.delete(user)
    db.commit()
    clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
