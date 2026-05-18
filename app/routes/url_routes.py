import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import create_url_rate_limiter
from app.db.database import get_db_session
from app.models.user import User
from app.routes.auth_routes import get_current_user, get_optional_current_user
from app.schemas.url import (
    ClickEventResponse,
    DailyClickCount,
    LabelCount,
    URLAnalyticsResponse,
    URLCreate,
    URLDailyAnalyticsResponse,
    URLDetailsResponse,
    UserAnalyticsOverviewResponse,
    UserURLListResponse,
    OverviewTrendPoint,
    TopLinkPerformance,
    URLResponse,
)
from app.services.url_service import (
    create_shortened_url,
    delete_shortened_url_by_code,
    get_click_count_for_url,
    get_daily_click_counts_for_url,
    get_recent_clicks_for_url,
    get_top_referrers_for_url,
    get_url_count_by_owner,
    get_shortened_url_by_code,
    get_urls_by_owner,
    get_device_breakdown_for_url,
    get_user_analytics_overview,
    record_click_event,
)
from app.services.ai_service import (
    create_ai_insight,
    get_latest_ai_insight_for_url,
    summarize_url,
)
from app.services.qr_service import create_branded_qr_svg

router = APIRouter(prefix="/urls", tags=["urls"])
logger = logging.getLogger(__name__)


def _build_short_url(short_code: str) -> str:
    base = settings.public_base_url.rstrip("/")
    return f"{base}/{short_code}"


def _to_url_response(shortened_url) -> URLResponse:
    response = URLResponse.model_validate(shortened_url)
    response.short_url = _build_short_url(shortened_url.short_code)
    return response


def _to_url_response_with_clicks(shortened_url, total_clicks: int) -> URLResponse:
    response = _to_url_response(shortened_url)
    response.total_clicks = total_clicks
    return response


def _ensure_analytics_access(shortened_url, current_user: User | None) -> None:
    if shortened_url.user_id is None:
        return

    if current_user is None or shortened_url.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this URL's analytics.",
        )


@router.post("", response_model=URLResponse, status_code=status.HTTP_201_CREATED)
async def create_url(
    payload: URLCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> URLResponse:
    client_ip = request.client.host if request.client else "unknown"
    if not create_url_rate_limiter.allow(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded: max 30 short links per hour per IP.",
        )

    try:
        created = await create_shortened_url(
            db=db,
            original_url=str(payload.original_url),
            user_id=current_user.id if current_user else None,
            custom_alias=payload.custom_alias,
        )
        response = _to_url_response(created)

        try:
            summary, tags, source_mode, _fallback_reason = await summarize_url(
                str(payload.original_url)
            )
            await create_ai_insight(
                db=db,
                original_url=str(payload.original_url),
                summary=summary,
                tags=tags,
                user_id=current_user.id if current_user else None,
                short_code=created.short_code,
            )
            response.ai_summary = summary
            response.ai_tags = tags
            response.ai_source_mode = source_mode
        except Exception:
            # Do not fail URL shortening if AI enrichment fails.
            logger.exception("AI summarization failed for short_code=%s", created.short_code)

        return response
    except ValueError as exc:
        detail = str(exc)
        if "already in use" in detail:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
        if "reserved" in detail:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.get("/mine", response_model=UserURLListResponse)
async def get_my_urls(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, min_length=1, max_length=200),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserURLListResponse:
    total_count = await get_url_count_by_owner(
        db=db,
        owner_id=current_user.id,
        query=q,
        start_date=start_date,
        end_date=end_date,
    )
    urls = await get_urls_by_owner(
        db=db,
        owner_id=current_user.id,
        limit=limit,
        offset=offset,
        query=q,
        start_date=start_date,
        end_date=end_date,
    )
    has_more = offset + len(urls) < total_count
    return UserURLListResponse(
        total_count=total_count,
        limit=limit,
        offset=offset,
        has_more=has_more,
        next_offset=(offset + limit) if has_more else None,
        items=[_to_url_response_with_clicks(url, total_clicks) for url, total_clicks in urls],
    )


@router.get("/analytics/overview", response_model=UserAnalyticsOverviewResponse)
async def get_my_analytics_overview(
    days: int = Query(default=7, ge=1, le=90),
    tz_offset_minutes: int = Query(default=0, ge=-720, le=840),
    compare_previous: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserAnalyticsOverviewResponse:
    (
        total_links,
        total_clicks,
        active_links,
        average_clicks_per_active_link,
        top_link_share_percent,
        direct_traffic_share_percent,
        best_day,
        best_day_clicks,
        start_date,
        end_date,
        trend,
        hourly_distribution,
        weekday_distribution,
        top_links,
        top_referrers,
        device_breakdown,
        previous_total_clicks,
        click_change_percent,
    ) = await get_user_analytics_overview(
        db=db,
        owner_id=current_user.id,
        days=days,
        tz_offset_minutes=tz_offset_minutes,
        compare_previous=compare_previous,
    )
    return UserAnalyticsOverviewResponse(
        total_links=total_links,
        total_clicks=total_clicks,
        active_links=active_links,
        average_clicks_per_active_link=average_clicks_per_active_link,
        top_link_share_percent=top_link_share_percent,
        direct_traffic_share_percent=direct_traffic_share_percent,
        best_day=best_day,
        best_day_clicks=best_day_clicks,
        previous_total_clicks=previous_total_clicks,
        click_change_percent=click_change_percent,
        window_days=days,
        timezone_offset_minutes=tz_offset_minutes,
        start_date=start_date,
        end_date=end_date,
        trend=[OverviewTrendPoint(date=day, clicks=clicks) for day, clicks in trend],
        hourly_distribution=[
            LabelCount(label=label, clicks=clicks) for label, clicks in hourly_distribution
        ],
        weekday_distribution=[
            LabelCount(label=label, clicks=clicks) for label, clicks in weekday_distribution
        ],
        top_links=[
            TopLinkPerformance(
                short_code=url.short_code,
                short_url=_build_short_url(url.short_code),
                original_url=url.original_url,
                clicks=clicks,
            )
            for url, clicks in top_links
        ],
        top_referrers=[LabelCount(label=label, clicks=clicks) for label, clicks in top_referrers],
        device_breakdown=[LabelCount(label=label, clicks=clicks) for label, clicks in device_breakdown],
    )


@router.get("/{short_code}/details", response_model=URLDetailsResponse)
async def get_url_details(
    short_code: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> URLDetailsResponse:
    shortened_url = await get_shortened_url_by_code(db=db, short_code=short_code)
    if not shortened_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found."
        )

    _ensure_analytics_access(shortened_url, current_user)

    total_clicks = await get_click_count_for_url(db=db, url_id=shortened_url.id)
    latest_insight = await get_latest_ai_insight_for_url(db=db, url_id=shortened_url.id)
    ai_tags: list[str] = []
    ai_summary: str | None = None
    ai_last_updated_at = None
    if latest_insight:
        ai_summary = latest_insight.summary
        ai_tags = [tag.strip() for tag in latest_insight.tags.split(",") if tag.strip()]
        ai_last_updated_at = latest_insight.created_at

    return URLDetailsResponse(
        id=shortened_url.id,
        short_code=shortened_url.short_code,
        short_url=_build_short_url(shortened_url.short_code),
        original_url=shortened_url.original_url,
        created_at=shortened_url.created_at,
        total_clicks=total_clicks,
        ai_summary=ai_summary,
        ai_tags=ai_tags,
        ai_last_updated_at=ai_last_updated_at,
    )


@router.get("/{short_code}/qr.svg", include_in_schema=False)
async def get_branded_qr_svg(
    short_code: str,
    theme: str = Query(default="ember", max_length=24),
    effect: str = Query(default="glow", max_length=24),
    label: str | None = Query(default=None, max_length=72),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    shortened_url = await get_shortened_url_by_code(db=db, short_code=short_code)
    if not shortened_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found."
        )

    svg = create_branded_qr_svg(
        short_url=_build_short_url(shortened_url.short_code),
        short_code=shortened_url.short_code,
        theme=theme,
        effect=effect,
        label=label,
    )
    filename = f"{shortened_url.short_code}-qr.svg"
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.delete("/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    short_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await delete_shortened_url_by_code(db=db, short_code=short_code, owner_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{short_code}", status_code=status.HTTP_301_MOVED_PERMANENTLY)
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

    return RedirectResponse(url=shortened_url.original_url, status_code=301)


@router.get("/r/{short_code}", status_code=status.HTTP_301_MOVED_PERMANENTLY, include_in_schema=False)
async def redirect_to_original_url_legacy(
    short_code: str, request: Request, db: AsyncSession = Depends(get_db_session)
) -> RedirectResponse:
    return await redirect_to_original_url(short_code=short_code, request=request, db=db)


@router.get("/{short_code}/analytics", response_model=URLAnalyticsResponse)
async def get_url_analytics(
    short_code: str,
    recent_limit: int = Query(default=10, ge=1, le=100),
    top_referrers_limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> URLAnalyticsResponse:
    shortened_url = await get_shortened_url_by_code(db=db, short_code=short_code)
    if not shortened_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found."
        )

    _ensure_analytics_access(shortened_url, current_user)

    total_clicks = await get_click_count_for_url(db=db, url_id=shortened_url.id)
    recent_clicks = await get_recent_clicks_for_url(
        db=db, url_id=shortened_url.id, limit=recent_limit
    )
    top_referrers = await get_top_referrers_for_url(
        db=db, url_id=shortened_url.id, limit=top_referrers_limit
    )
    device_breakdown = await get_device_breakdown_for_url(
        db=db, url_id=shortened_url.id
    )

    return URLAnalyticsResponse(
        short_code=shortened_url.short_code,
        total_clicks=total_clicks,
        recent_clicks_limit=recent_limit,
        recent_clicks=[ClickEventResponse.model_validate(click) for click in recent_clicks],
        top_referrers=[LabelCount(label=label, clicks=clicks) for label, clicks in top_referrers],
        device_breakdown=[LabelCount(label=label, clicks=clicks) for label, clicks in device_breakdown],
    )


@router.get("/{short_code}/analytics/daily", response_model=URLDailyAnalyticsResponse)
async def get_url_daily_analytics(
    short_code: str,
    days: int = Query(default=7, ge=1, le=90),
    tz_offset_minutes: int = Query(default=0, ge=-720, le=840),
    db: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> URLDailyAnalyticsResponse:
    shortened_url = await get_shortened_url_by_code(db=db, short_code=short_code)
    if not shortened_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found."
        )

    _ensure_analytics_access(shortened_url, current_user)

    daily_click_counts = await get_daily_click_counts_for_url(
        db=db, url_id=shortened_url.id, days=days, tz_offset_minutes=tz_offset_minutes
    )

    return URLDailyAnalyticsResponse(
        short_code=shortened_url.short_code,
        days=days,
        timezone_offset_minutes=tz_offset_minutes,
        start_date=daily_click_counts[0][0],
        end_date=daily_click_counts[-1][0],
        daily_clicks=[
            DailyClickCount(date=click_date, clicks=click_count)
            for click_date, click_count in daily_click_counts
        ],
    )
