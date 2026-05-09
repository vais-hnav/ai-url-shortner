import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.models.user import User
from app.routes.auth_routes import get_current_user, get_optional_current_user
from app.schemas.url import (
    ClickEventResponse,
    DailyClickCount,
    URLAnalyticsResponse,
    URLCreate,
    URLDailyAnalyticsResponse,
    UserURLListResponse,
    URLResponse,
)
from app.services.url_service import (
    create_shortened_url,
    get_click_count_for_url,
    get_daily_click_counts_for_url,
    get_recent_clicks_for_url,
    get_url_count_by_owner,
    get_shortened_url_by_code,
    get_urls_by_owner,
    record_click_event,
)

router = APIRouter(prefix="/urls", tags=["urls"])
logger = logging.getLogger(__name__)


@router.post("", response_model=URLResponse, status_code=status.HTTP_201_CREATED)
async def create_url(
    payload: URLCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> URLResponse:
    try:
        created = await create_shortened_url(
            db=db,
            original_url=str(payload.original_url),
            user_id=current_user.id if current_user else None,
            custom_alias=payload.custom_alias,
        )
        return URLResponse.model_validate(created)
    except ValueError as exc:
        detail = str(exc)
        if "already in use" in detail:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.get("/mine", response_model=UserURLListResponse)
async def get_my_urls(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserURLListResponse:
    total_count = await get_url_count_by_owner(db=db, owner_id=current_user.id)
    urls = await get_urls_by_owner(
        db=db, owner_id=current_user.id, limit=limit, offset=offset
    )
    has_more = offset + len(urls) < total_count
    return UserURLListResponse(
        total_count=total_count,
        limit=limit,
        offset=offset,
        has_more=has_more,
        next_offset=(offset + limit) if has_more else None,
        items=[URLResponse.model_validate(url) for url in urls],
    )


@router.get("/{short_code}", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def redirect_to_original_url(
    short_code: str, request: Request, db: AsyncSession = Depends(get_db_session)
) -> RedirectResponse:
    shortened_url = await get_shortened_url_by_code(db=db, short_code=short_code)
    if not shortened_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found."
        )

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

    return RedirectResponse(url=shortened_url.original_url, status_code=307)


@router.get("/{short_code}/analytics", response_model=URLAnalyticsResponse)
async def get_url_analytics(
    short_code: str, db: AsyncSession = Depends(get_db_session)
) -> URLAnalyticsResponse:
    shortened_url = await get_shortened_url_by_code(db=db, short_code=short_code)
    if not shortened_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found."
        )

    total_clicks = await get_click_count_for_url(db=db, url_id=shortened_url.id)
    recent_clicks = await get_recent_clicks_for_url(db=db, url_id=shortened_url.id)

    return URLAnalyticsResponse(
        short_code=shortened_url.short_code,
        total_clicks=total_clicks,
        recent_clicks=[ClickEventResponse.model_validate(click) for click in recent_clicks],
    )


@router.get("/{short_code}/analytics/daily", response_model=URLDailyAnalyticsResponse)
async def get_url_daily_analytics(
    short_code: str,
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db_session),
) -> URLDailyAnalyticsResponse:
    shortened_url = await get_shortened_url_by_code(db=db, short_code=short_code)
    if not shortened_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found."
        )

    daily_click_counts = await get_daily_click_counts_for_url(
        db=db, url_id=shortened_url.id, days=days
    )

    return URLDailyAnalyticsResponse(
        short_code=shortened_url.short_code,
        days=days,
        daily_clicks=[
            DailyClickCount(date=click_date, clicks=click_count)
            for click_date, click_count in daily_click_counts
        ],
    )
