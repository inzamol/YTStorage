from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path

# Core configurations
from src.core.config import get_settings
from src.core.logging import logger

# Routers
from src.api.routers import auth, dashboard, video

settings = get_settings()
app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For production, you may want to restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))

# --- Exception Handlers ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Exception caught: {exc}")
    status_code = getattr(exc, "status_code", 500)
    return templates.TemplateResponse(
        "error.html", 
        {"request": request, "status_code": status_code, "message": str(exc)},
        status_code=status_code
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP Exception caught: {exc.detail}")
    return templates.TemplateResponse(
        "error.html", 
        {"request": request, "status_code": exc.status_code, "message": exc.detail},
        status_code=exc.status_code
    )

# --- Include Routers ---

app.include_router(dashboard.router)
app.include_router(auth.router)
app.include_router(video.router)