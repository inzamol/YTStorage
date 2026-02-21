from celery import Celery

celery = Celery(
    "yt_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

# celery.conf.task_always_eager = True
