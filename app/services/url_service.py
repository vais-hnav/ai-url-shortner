import secrets
import string
from datetime import date, timedelta, timezone, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.click_event import ClickEvent
from app.models.url import ShortenedURL

ALPHABET = string.ascii_letters + string.digits
SHORT_CODE_LENGTH = 7
MAX_GENERATION_ATTEMPTS = 10


def _generate_short_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(SHORT_CODE_LENGTH))


async def create_shortened_url(
    db: AsyncSession, original_url: str, user_id: int | None = None
) -> ShortenedURL:
    for _ in range(MAX_GENERATION_ATTEMPTS):
        short_code = _generate_short_code()
        existing = await db.scalar(
            select(ShortenedURL).where(ShortenedURL.short_code == short_code)
        )
        if existing:
            continue

        shortened_url = ShortenedURL(
            original_url=original_url, short_code=short_code, user_id=user_id
        )
        db.add(shortened_url)
        await db.commit()
        await db.refresh(shortened_url)
        return shortened_url

    raise RuntimeError("Failed to generate a unique short code.")


async def get_shortened_url_by_code(
    db: AsyncSession, short_code: str
) -> ShortenedURL | None:
    return await db.scalar(
        select(ShortenedURL).where(ShortenedURL.short_code == short_code)
    )


async def record_click_event(
    db: AsyncSession,
    url_id: int,
    referrer: str | None,
    user_agent: str | None,
    ip_address: str | None,
) -> ClickEvent:
    click_event = ClickEvent(
        url_id=url_id, referrer=referrer, user_agent=user_agent, ip_address=ip_address
    )
    db.add(click_event)
    await db.commit()
    await db.refresh(click_event)
    return click_event


async def get_click_count_for_url(db: AsyncSession, url_id: int) -> int:
    count = await db.scalar(select(func.count()).select_from(ClickEvent).where(ClickEvent.url_id == url_id))
    return int(count or 0)


async def get_recent_clicks_for_url(
    db: AsyncSession, url_id: int, limit: int = 10
) -> list[ClickEvent]:
    result = await db.scalars(
        select(ClickEvent)
        .where(ClickEvent.url_id == url_id)
        .order_by(ClickEvent.created_at.desc())
        .limit(limit)
    )
    return list(result)


async def get_daily_click_counts_for_url(
    db: AsyncSession, url_id: int, days: int
) -> list[tuple[date, int]]:
    utc_today = datetime.now(timezone.utc).date()
    start_date = utc_today - timedelta(days=days - 1)

    rows = await db.execute(
        select(
            func.date(ClickEvent.created_at).label("day"),
            func.count(ClickEvent.id).label("clicks"),
        )
        .where(ClickEvent.url_id == url_id)
        .where(ClickEvent.created_at >= start_date)
        .group_by(func.date(ClickEvent.created_at))
        .order_by(func.date(ClickEvent.created_at))
    )

    click_map = {row.day: int(row.clicks) for row in rows}

    daily_series: list[tuple[date, int]] = []
    for day_offset in range(days):
        current_day = start_date + timedelta(days=day_offset)
        daily_series.append((current_day, click_map.get(current_day, 0)))

    return daily_series
