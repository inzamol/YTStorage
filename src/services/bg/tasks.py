from sqlalchemy.orm import Session
from src.db import SessionLocal
from src.models.user import User
from src.models.yt import VideoUploadJob, YouTubeAccount
from src.services.bg.cs import celery
from src.services.upload_service import UploadService
import os


@celery.task(bind=True)
def process_upload(self, job_id: str):
    db: Session = SessionLocal()
    job = db.query(VideoUploadJob).get(job_id)
    try:
        job.status = "processing"
        db.commit()

        us = UploadService()
        video_id = us.upload_video(job.youtube_account.refresh_token, job.file_path, job.title, job.description, job.category_id, job.privacy_status)

        job.status = "uploaded"
        job.video_id = video_id
        db.commit()

        # Clean up the local file after successful upload
        if os.path.exists(job.file_path):
            os.remove(job.file_path)

    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
        raise e
    finally:
        db.close()