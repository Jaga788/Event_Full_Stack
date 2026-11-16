
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import create_tables, get_db
from app.routers.auth import router as auth_router
from app.routers.ai_planner import router as ai_planner_router
from app.routers.bookings import router as bookings_router
from app.routers.cart import router as cart_router
from app.routers.categories import router as categories_router
from app.routers.events import router as events_router
from app.routers.favorites import router as favorites_router
from app.routers.messages import router as messages_router
from app.routers.packages import router as packages_router
from app.routers.service_listings import router as services_router
from app.routers.uploads import router as uploads_router
from app.routers.users import router as users_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    if (
        settings.JWT_SECRET_KEY is None
        or len(settings.JWT_SECRET_KEY.get_secret_value()) < 32
    ):
        raise RuntimeError(
            "Set JWT_SECRET_KEY in .env to a random secret of at least 32 characters"
        )
    create_tables()
    yield


app = FastAPI(title="Event Management API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://event-full-stack-sigma.vercel.app",
        "http://localhost:5173",
        *[
            origin.strip()
            for origin in settings.CORS_ORIGINS.split(",")
            if origin.strip()
        ],
    ],
    allow_origin_regex=(
        r"^https://event-full-stack-[a-z0-9-]+-pinisetti-jagadeeshs-projects"
        r"\.vercel\.app$"
    ),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(ai_planner_router)
app.include_router(cart_router)
app.include_router(favorites_router)
app.include_router(bookings_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(events_router)
app.include_router(messages_router)
app.include_router(packages_router)
app.include_router(services_router)
app.include_router(uploads_router)
app.mount(
    "/uploads",
    StaticFiles(directory=str(settings.UPLOAD_DIR), check_dir=False),
    name="uploads",
)

@app.get("/")
def home():
    return {"message": "Event Management Backend is running"}

@app.get("/health/db")
def check_database(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))
    return {
        "message": "Supabase database connected successfully",
        "result": result.scalar()
    }
