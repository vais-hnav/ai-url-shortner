# Create FastAPI application instance
# Add health check route
import logging

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.models.url import ShortenedURL
from app.routes import ai_router, auth_router, url_router
from app.services.url_service import get_shortened_url_by_code, record_click_event

app = FastAPI(title="AI URL Shortner")
logger = logging.getLogger(__name__)

app.mount("/web", StaticFiles(directory="app/web", html=True), name="web")
app.include_router(ai_router)
app.include_router(auth_router)
app.include_router(url_router)

@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/{short_code}", status_code=status.HTTP_301_MOVED_PERMANENTLY, include_in_schema=False)
async def root_short_redirect(
    short_code: str, request: Request, db: AsyncSession = Depends(get_db_session)
) -> RedirectResponse:
    shortened_url: ShortenedURL | None = await get_shortened_url_by_code(db=db, short_code=short_code)
    if not shortened_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found.")

    try:
        await record_click_event(
            db=db,
            url_id=shortened_url.id,
            referrer=request.headers.get("referer"),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except Exception:
        await db.rollback()
        logger.exception("Failed to record click event for short_code=%s", short_code)

    return RedirectResponse(url=shortened_url.original_url, status_code=301)
