from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
from pathlib import Path

from src.db import get_db
from src.models.user import User
from src.models.yt import YouTubeAccount, VideoUploadJob
from src.core.config import get_settings
from src.core.logging import logger

router = APIRouter(tags=["dashboard"])
settings = get_settings()

base_dir = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).first()
    jobs = []
    if user:
        jobs = db.query(VideoUploadJob).filter(
            VideoUploadJob.user_id == user.id,
            VideoUploadJob.status == 'uploaded'
        ).order_by(VideoUploadJob.created_at.desc()).limit(10).all()
    return templates.TemplateResponse("gdrive.html", {"request": request, "jobs": jobs, "user": user})

@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        return RedirectResponse("/auth/youtube")
        
    jobs = db.query(VideoUploadJob).filter(VideoUploadJob.user_id == user.id).order_by(VideoUploadJob.created_at.desc()).all()
    return templates.TemplateResponse("filemanager.html", {"request": request, "jobs": jobs, "user": user})

@router.get("/my-videos")
def my_videos(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        return RedirectResponse("/auth/youtube")
        
    yt_account = db.query(YouTubeAccount).filter(YouTubeAccount.user_id == user.id).first()
    if not yt_account or not yt_account.refresh_token:
        return RedirectResponse("/auth/youtube")

    creds = Credentials(
        None,
        refresh_token=yt_account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET
    )

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    
    videos = []
    try:
        channels_response = youtube.channels().list(mine=True, part="contentDetails").execute()
        if channels_response.get("items"):
            uploads_playlist_id = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            
            playlist_response = youtube.playlistItems().list(
                playlistId=uploads_playlist_id,
                part="snippet,status",
                maxResults=50
            ).execute()
            
            all_videos = playlist_response.get("items", [])
            videos = [v for v in all_videos if v.get("status", {}).get("privacyStatus") in ("public", "unlisted")]
    except Exception as e:
        logger.error(f"Error fetching YouTube videos: {e}")

    return templates.TemplateResponse("my_videos.html", {"request": request, "videos": videos, "user": user})
