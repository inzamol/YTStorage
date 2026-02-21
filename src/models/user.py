from src.models.basemodel import Base
from sqlalchemy import (
    Column, String, Text, ForeignKey,
    DateTime
)
from sqlalchemy.orm import relationship , declarative_base
from sqlalchemy.sql import func
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    password_hash = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    youtube_accounts = relationship(
        "YouTubeAccount",
        back_populates="user",
        cascade="all, delete-orphan"
    )