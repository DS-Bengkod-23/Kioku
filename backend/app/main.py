from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError
from app.config import settings
from app.rate_limit import limiter
from app.routers import auth, meetings, checkin, recordings, action_items

app = FastAPI(title="MeetMate API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={"detail": "Data bertentangan dengan data lain yang sudah ada. Coba muat ulang halaman."},
    )


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
