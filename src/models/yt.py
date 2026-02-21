from src.models.basemodel import Base
from sqlalchemy import (
    Column, String, Text, ForeignKey,
    DateTime, UniqueConstraint, Enum
)
from sqlalchemy.orm import relationship , declarative_base
from sqlalchemy.sql import func
import uuid
from src.models.utils import UploadStatus

class YouTubeAccount(Base):
    __tablename__ = "youtube_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="unique_user_channel"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"))

    google_account_email = Column(String(255))
    channel_id = Column(String(255))
    channel_title = Column(String(255))

    refresh_token = Column(Text, nullable=False)
    access_token = Column(Text)
    token_expiry = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="youtube_accounts")
    upload_jobs = relationship(
        "VideoUploadJob",
        back_populates="youtube_account",
        cascade="all, delete-orphan"
    )


class VideoUploadJob(Base):
    __tablename__ = "video_upload_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(String(36), ForeignKey("users.id"))
    youtube_account_id = Column(String(36), ForeignKey("youtube_accounts.id"))

    title = Column(Text, nullable=False)
    description = Column(Text)
    tags = Column(Text) # Store as JSON string in SQLite
    category_id = Column(String(20))
    privacy_status = Column(String(20), default="private")

    file_path = Column(Text, nullable=False)

    status = Column(Enum(UploadStatus), default=UploadStatus.pending)
    error_message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    youtube_account = relationship("YouTubeAccount", back_populates="upload_jobs")
    youtube_video = relationship(
        "YouTubeVideo",
        back_populates="upload_job",
        uselist=False
    )


class YouTubeVideo(Base):
    __tablename__ = "youtube_videos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    upload_job_id = Column(
        String(36),
        ForeignKey("video_upload_jobs.id", ondelete="CASCADE"),
        unique=True
    )

    youtube_video_id = Column(String(255), nullable=False)
    youtube_url = Column(Text)

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    upload_job = relationship("VideoUploadJob", back_populates="youtube_video")