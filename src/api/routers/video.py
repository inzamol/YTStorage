from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
import shutil
import uuid
import httpx
import yt_dlp
from pathlib import Path

from src.db import get_db
from src.models.user import User
from src.models.yt import YouTubeAccount, VideoUploadJob
from src.services.bg.tasks import process_upload
from src.core.logging import logger

router = APIRouter(tags=["video"])

@router.post("/upload")
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

    # Save original mimetype so we don't rely on google's guess
    original_mime = file.content_type or "application/octet-stream"
    logger.info(f"Received file upload '{file.filename}' with mimetype '{original_mime}'")

    # Create job in database
    job = VideoUploadJob(
        user_id=user.id,
        youtube_account_id=yt_account.id,
        title=title,
        description=description,
        file_path=str(temp_file_path),
        mime_type=original_mime,
        status="pending",
        privacy_status="unlisted"
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Trigger background task
    process_upload.delay(str(job.id))
    return RedirectResponse(url="/dashboard", status_code=303)

@router.get("/download/{video_id}")
async def download_video(video_id: str):
    logger.info(f"Initiating download for video ID: {video_id}")
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
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        headers = {
            'Content-Disposition': f'attachment; filename="{safe_title}.{ext}"'
        }
        return StreamingResponse(iterfile(), media_type="application/octet-stream", headers=headers)
    except Exception as e:
        logger.error(f"Error downloading video {video_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download video: {str(e)}")
