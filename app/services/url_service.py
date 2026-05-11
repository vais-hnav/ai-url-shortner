import secrets
import string
from datetime import date, timedelta, timezone, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.click_event import ClickEvent
from app.models.url import ShortenedURL

ALPHABET = string.ascii_letters + string.digits
SHORT_CODE_LENGTH = 7
MAX_GENERATION_ATTEMPTS = 10
ALIAS_ALPHABET = string.ascii_letters + string.digits + "-_"
ALIAS_MIN_LENGTH = 3
ALIAS_MAX_LENGTH = 32
RESERVED_ALIASES = {
    "web",
    "urls",
    "auth",
    "ai",
    "docs",
    "redoc",
    "openapi.json",
    "favicon.ico",
    "health",
    "admin",
}


def _generate_short_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(SHORT_CODE_LENGTH))


def _normalize_and_validate_alias(raw_alias: str) -> str:
    alias = raw_alias.strip().lower()
    if not alias:
        raise ValueError("custom_alias cannot be empty.")
    if len(alias) < ALIAS_MIN_LENGTH or len(alias) > ALIAS_MAX_LENGTH:
        raise ValueError(
            f"custom_alias length must be between {ALIAS_MIN_LENGTH} and {ALIAS_MAX_LENGTH}."
        )
    if any(char not in ALIAS_ALPHABET for char in alias):
        raise ValueError(
            "custom_alias can only contain letters, numbers, hyphen, and underscore."
        )
    if alias[0] in "-_" or alias[-1] in "-_":
        raise ValueError("custom_alias cannot start or end with hyphen or underscore.")
    if "--" in alias or "__" in alias or "-_" in alias or "_-" in alias:
        raise ValueError("custom_alias cannot contain repeated or mixed separators.")
    if alias.lower() in RESERVED_ALIASES:
        raise ValueError("custom_alias is reserved and cannot be used.")
    return alias


async def create_shortened_url(
    db: AsyncSession,
    original_url: str,
    user_id: int | None = None,
    custom_alias: str | None = None,
) -> ShortenedURL:
    if custom_alias:
        alias = _normalize_and_validate_alias(custom_alias)
        existing_alias = await db.scalar(
            select(ShortenedURL).where(func.lower(ShortenedURL.short_code) == alias)
        )
        if existing_alias:
            raise ValueError("custom_alias is already in use.")

        shortened_url = ShortenedURL(
            original_url=original_url, short_code=alias, user_id=user_id
        )
        db.add(shortened_url)
        await db.commit()
        await db.refresh(shortened_url)
        return shortened_url

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


async def get_top_referrers_for_url(
    db: AsyncSession, url_id: int, limit: int = 5
) -> list[tuple[str, int]]:
    rows = await db.execute(
        select(
            func.coalesce(ClickEvent.referrer, "direct").label("referrer"),
            func.count(ClickEvent.id).label("clicks"),
        )
        .where(ClickEvent.url_id == url_id)
        .group_by(func.coalesce(ClickEvent.referrer, "direct"))
        .order_by(func.count(ClickEvent.id).desc())
        .limit(limit)
    )
    return [(str(row.referrer), int(row.clicks)) for row in rows]


def _device_label_from_user_agent(user_agent: str | None) -> str:
    ua = (user_agent or "").lower()
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        return "mobile"
    if "ipad" in ua or "tablet" in ua:
        return "tablet"
    if ua:
        return "desktop"
    return "unknown"


async def get_device_breakdown_for_url(
    db: AsyncSession, url_id: int
) -> list[tuple[str, int]]:
    rows = await db.scalars(
        select(ClickEvent.user_agent).where(ClickEvent.url_id == url_id)
    )
    counts: dict[str, int] = {"desktop": 0, "mobile": 0, "tablet": 0, "unknown": 0}
    for ua in rows:
        label = _device_label_from_user_agent(ua)
        counts[label] = counts.get(label, 0) + 1
    return [(label, count) for label, count in counts.items() if count > 0]


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


async def get_urls_by_owner(
    db: AsyncSession, owner_id: int, limit: int = 50, offset: int = 0
) -> list[ShortenedURL]:
    result = await db.scalars(
        select(ShortenedURL)
        .where(ShortenedURL.user_id == owner_id)
        .order_by(ShortenedURL.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result)


async def get_url_count_by_owner(db: AsyncSession, owner_id: int) -> int:
    count = await db.scalar(
        select(func.count()).select_from(ShortenedURL).where(ShortenedURL.user_id == owner_id)
    )
    return int(count or 0)


async def delete_shortened_url_by_code(
    db: AsyncSession, short_code: str, owner_id: int
) -> bool:
    """Delete a URL if owned by the specified user."""
    shortened_url = await db.scalar(
        select(ShortenedURL).where(ShortenedURL.short_code == short_code)
    )
    if not shortened_url:
        raise ValueError("URL not found.")

    if shortened_url.user_id != owner_id:
        raise PermissionError("You do not have permission to delete this URL.")

    await db.execute(delete(ClickEvent).where(ClickEvent.url_id == shortened_url.id))
    await db.delete(shortened_url)
    await db.commit()
    return True
