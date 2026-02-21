from fastapi import FastAPI, Request, Depends, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from google_auth_oauthlib.flow import Flow
from pathlib import Path
from sqlalchemy.orm import Session
import shutil
import uuid
from src.db import get_db
from src.models.user import User
from src.models.yt import YouTubeAccount, VideoUploadJob
from src.services.bg.tasks import process_upload

app = FastAPI()

CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
REDIRECT_URI = "http://localhost:8000/auth/youtube/callback"

base_dir = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

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
        status="pending"
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