from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, meetings, checkin, recordings, action_items

app = FastAPI(title="MeetMate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router, prefix="/api/v1")
app.include_router(meetings.router, prefix="/api/v1/meetings")
app.include_router(checkin.router, prefix="/api/v1")
app.include_router(recordings.router, prefix="/api/v1/meetings")
app.include_router(action_items.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "env": settings.APP_ENV}
