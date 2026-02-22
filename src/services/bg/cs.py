from celery import Celery
from src.core.config import get_settings

settings = get_settings()

celery = Celery(
    "yt_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# celery.conf.task_always_eager = True
