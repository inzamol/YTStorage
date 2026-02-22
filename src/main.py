from fastapi import FastAPI, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
import httpx
import yt_dlp
from google_auth_oauthlib.flow import Flow
from pathlib import Path
from sqlalchemy.orm import Session
import shutil
import uuid
from src.db import get_db
from src.models.user import User
from src.models.yt import YouTubeAccount, VideoUploadJob
from src.services.bg.tasks import process_upload
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

app = FastAPI()

CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/youtube"]
REDIRECT_URI = "http://localhost:8000/auth/youtube/callback"

base_dir = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global Excepion caught: {exc}")
    status_code = getattr(exc, "status_code", 500)
    return templates.TemplateResponse(
        "error.html", 
        {"request": request, "status_code": status_code, "message": str(exc)},
        status_code=status_code
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    print(f"HTTP Excepion caught: {exc.detail}")
    return templates.TemplateResponse(
        "error.html", 
        {"request": request, "status_code": exc.status_code, "message": exc.detail},
        status_code=exc.status_code
    )

@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).first()
    jobs = []
    if user:
        jobs = db.query(VideoUploadJob).filter(
            VideoUploadJob.user_id == user.id,
            VideoUploadJob.status == 'uploaded'
        ).order_by(VideoUploadJob.created_at.desc()).limit(10).all()
    return templates.TemplateResponse("gdrive.html", {"request": request, "jobs": jobs, "user": user})

@app.get("/my-videos")
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
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
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
        print(f"Error fetching YouTube videos: {e}")

    return templates.TemplateResponse("my_videos.html", {"request": request, "videos": videos, "user": user})

@app.get("/download/{video_id}")
async def download_video(video_id: str):
    try:
        ydl_opts = {'format': 'best', 'quiet': True, 'no_color': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            video_url = info['url']
            ext = info.get('ext', 'mp4')
            title = info.get('title', video_id)

        async def iterfile():
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", video_url) as response:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        yield chunk

        # Force download instead of inline play
        # To handle exotic titles safely in header, encode ascii
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        headers = {
            'Content-Disposition': f'attachment; filename="{safe_title}.{ext}"'
        }
        return StreamingResponse(iterfile(), media_type="application/octet-stream", headers=headers)
    except Exception as e:
        print(f"Error downloading video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")

@app.get("/auth/youtube")
def auth_youtube():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    return RedirectResponse(authorization_url)


@app.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        return RedirectResponse("/auth/youtube")
        
    jobs = db.query(VideoUploadJob).filter(VideoUploadJob.user_id == user.id).order_by(VideoUploadJob.created_at.desc()).all()
    
    return templates.TemplateResponse("filemanager.html", {"request": request, "jobs": jobs, "user": user})


@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    user = db.query(User).first()
    if not user:
        return {"error": "User not found"}
        
    yt_account = db.query(YouTubeAccount).filter(YouTubeAccount.user_id == user.id).first()
    if not yt_account:
        return {"error": "YouTube account not linked"}

    # Save uploaded file to temp directory
    temp_dir = Path("temp_videos")
    temp_dir.mkdir(exist_ok=True)
    temp_file_path = temp_dir / f"{uuid.uuid4()}_{file.filename}"

    with temp_file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create job in database
    job = VideoUploadJob(
        user_id=user.id,
        youtube_account_id=yt_account.id,
        title=title,
        description=description,
        file_path=str(temp_file_path),
        status="pending",
        privacy_status="unlisted"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Trigger background task
    process_upload.delay(str(job.id))
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/auth/youtube/callback")
def youtube_callback(request: Request, code: str, db: Session = Depends(get_db)):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    flow.fetch_token(code=code)
    credentials = flow.credentials

    refresh_token = credentials.refresh_token
    access_token = credentials.token

    # 🔥 SAVE refresh_token in your DB linked to user
    print(refresh_token)

    # For now, get or create a dummy user since we don't have app authentication yet
    user = db.query(User).first()
    if not user:
        user = User(email="dummy@example.com", name="Dummy User")
        db.add(user)
        db.commit()
    
    # Save the YouTube Account Token
    yt_account = db.query(YouTubeAccount).filter(YouTubeAccount.user_id == user.id).first()
    if not yt_account:
        yt_account = YouTubeAccount(
            user_id=user.id,
            refresh_token=refresh_token,
            access_token=access_token
        )
        db.add(yt_account)
    else:
        # If refreshing, we might only get a new access token
        if refresh_token:
            yt_account.refresh_token = refresh_token
        yt_account.access_token = access_token
    
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)