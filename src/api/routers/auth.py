import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from src.db import get_db
from src.models.user import User
from src.models.yt import YouTubeAccount
from src.core.config import get_settings
from src.core.logging import logger

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

CLIENT_SECRETS_FILE = "credentials.json"
REDIRECT_URI = "http://localhost:8000/auth/youtube/callback"

@router.get("/youtube")
def auth_youtube():
    logger.info("Initiating YouTube OAuth flow")
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=settings.YOUTUBE_SCOPES,
        redirect_uri=REDIRECT_URI
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    return RedirectResponse(authorization_url)

@router.get("/youtube/callback")
def youtube_callback(request: Request, code: str, db: Session = Depends(get_db)):
    logger.info("Received YouTube OAuth callback")
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=settings.YOUTUBE_SCOPES,
        redirect_uri=REDIRECT_URI
    )

    flow.fetch_token(code=code)
    credentials = flow.credentials

    # For now, we assume a single user system.
    user = db.query(User).first()
    if not user:
        user = User(email="user@example.com", name="YT Manager User", hashed_password="hashed_password")
        db.add(user)
        db.commit()
        db.refresh(user)

    yt_account = db.query(YouTubeAccount).filter(YouTubeAccount.user_id == user.id).first()
    if not yt_account:
        yt_account = YouTubeAccount(
            user_id=user.id,
            channel_id="pending",
            access_token=credentials.token,
            refresh_token=credentials.refresh_token
        )
        db.add(yt_account)
    else:
        yt_account.access_token = credentials.token
        if credentials.refresh_token:
            yt_account.refresh_token = credentials.refresh_token

    db.commit()
    logger.info(f"Successfully authenticated YouTube account for user {user.id}")
    return RedirectResponse(url="/dashboard", status_code=303)
