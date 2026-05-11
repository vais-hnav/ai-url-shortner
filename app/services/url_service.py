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


def _window_bounds_from_offset(days: int, tz_offset_minutes: int) -> tuple[date, date, datetime, datetime]:
    offset = timedelta(minutes=tz_offset_minutes)
    now_utc = datetime.now(timezone.utc)
    local_today = (now_utc + offset).date()
    start_date = local_today - timedelta(days=days - 1)
    end_date = local_today

    utc_start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc) - offset
    utc_end = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc) - offset
    return start_date, end_date, utc_start, utc_end


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
    db: AsyncSession, url_id: int, days: int, tz_offset_minutes: int = 0
) -> list[tuple[date, int]]:
    start_date, _end_date, utc_start, utc_end = _window_bounds_from_offset(days, tz_offset_minutes)
    rows = await db.scalars(
        select(ClickEvent.created_at)
        .where(ClickEvent.url_id == url_id)
        .where(ClickEvent.created_at >= utc_start)
        .where(ClickEvent.created_at < utc_end)
    )
    click_map: dict[date, int] = {}
    offset = timedelta(minutes=tz_offset_minutes)
    for created_at in rows:
        local_day = (created_at + offset).date()
        click_map[local_day] = click_map.get(local_day, 0) + 1

    daily_series: list[tuple[date, int]] = []
    for day_offset in range(days):
        current_day = start_date + timedelta(days=day_offset)
        daily_series.append((current_day, click_map.get(current_day, 0)))

    return daily_series


async def get_urls_by_owner(
    db: AsyncSession,
    owner_id: int,
    limit: int = 50,
    offset: int = 0,
    query: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[tuple[ShortenedURL, int]]:
    stmt = (
        select(
            ShortenedURL,
            func.count(ClickEvent.id).label("total_clicks"),
        )
        .outerjoin(ClickEvent, ClickEvent.url_id == ShortenedURL.id)
        .where(ShortenedURL.user_id == owner_id)
    )

    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            ShortenedURL.short_code.ilike(pattern) | ShortenedURL.original_url.ilike(pattern)
        )

    if start_date:
        stmt = stmt.where(ShortenedURL.created_at >= start_date)
    if end_date:
        stmt = stmt.where(ShortenedURL.created_at < (end_date + timedelta(days=1)))

    rows = await db.execute(
        stmt.group_by(ShortenedURL.id)
        .order_by(ShortenedURL.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return [(url, int(total_clicks or 0)) for url, total_clicks in rows]


async def get_url_count_by_owner(
    db: AsyncSession,
    owner_id: int,
    query: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    stmt = select(func.count()).select_from(ShortenedURL).where(ShortenedURL.user_id == owner_id)
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            ShortenedURL.short_code.ilike(pattern) | ShortenedURL.original_url.ilike(pattern)
        )
    if start_date:
        stmt = stmt.where(ShortenedURL.created_at >= start_date)
    if end_date:
        stmt = stmt.where(ShortenedURL.created_at < (end_date + timedelta(days=1)))
    count = await db.scalar(stmt)
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


async def get_user_analytics_overview(
    db: AsyncSession, owner_id: int, days: int = 7, tz_offset_minutes: int = 0, compare_previous: bool = False
) -> tuple[
    int,
    int,
    date,
    date,
    list[tuple[date, int]],
    list[tuple[ShortenedURL, int]],
    list[tuple[str, int]],
    list[tuple[str, int]],
    int | None,
    float | None,
]:
    total_links = await db.scalar(
        select(func.count()).select_from(ShortenedURL).where(ShortenedURL.user_id == owner_id)
    )
    total_links_int = int(total_links or 0)

    total_clicks = await db.scalar(
        select(func.count(ClickEvent.id))
        .select_from(ClickEvent)
        .join(ShortenedURL, ShortenedURL.id == ClickEvent.url_id)
        .where(ShortenedURL.user_id == owner_id)
    )
    total_clicks_int = int(total_clicks or 0)

    start_date, end_date, utc_start, utc_end = _window_bounds_from_offset(days, tz_offset_minutes)

    rows = await db.scalars(
        select(ClickEvent.created_at)
        .select_from(ClickEvent)
        .join(ShortenedURL, ShortenedURL.id == ClickEvent.url_id)
        .where(ShortenedURL.user_id == owner_id)
        .where(ClickEvent.created_at >= utc_start)
        .where(ClickEvent.created_at < utc_end)
    )
    click_map: dict[date, int] = {}
    offset = timedelta(minutes=tz_offset_minutes)
    for created_at in rows:
        local_day = (created_at + offset).date()
        click_map[local_day] = click_map.get(local_day, 0) + 1

    trend: list[tuple[date, int]] = []
    for day_offset in range(days):
        day = start_date + timedelta(days=day_offset)
        trend.append((day, click_map.get(day, 0)))

    top_links_rows = await db.execute(
        select(
            ShortenedURL,
            func.count(ClickEvent.id).label("clicks"),
        )
        .join(ClickEvent, ClickEvent.url_id == ShortenedURL.id)
        .where(ShortenedURL.user_id == owner_id)
        .where(ClickEvent.created_at >= utc_start)
        .where(ClickEvent.created_at < utc_end)
        .group_by(ShortenedURL.id)
        .order_by(func.count(ClickEvent.id).desc(), ShortenedURL.created_at.desc())
        .limit(5)
    )
    top_links: list[tuple[ShortenedURL, int]] = [
        (url, int(clicks or 0)) for url, clicks in top_links_rows
    ]

    top_referrers_rows = await db.execute(
        select(
            func.coalesce(ClickEvent.referrer, "direct").label("referrer"),
            func.count(ClickEvent.id).label("clicks"),
        )
        .select_from(ClickEvent)
        .join(ShortenedURL, ShortenedURL.id == ClickEvent.url_id)
        .where(ShortenedURL.user_id == owner_id)
        .where(ClickEvent.created_at >= utc_start)
        .where(ClickEvent.created_at < utc_end)
        .group_by(func.coalesce(ClickEvent.referrer, "direct"))
        .order_by(func.count(ClickEvent.id).desc())
        .limit(5)
    )
    top_referrers = [(str(referrer), int(clicks or 0)) for referrer, clicks in top_referrers_rows]

    user_agent_rows = await db.scalars(
        select(ClickEvent.user_agent)
        .select_from(ClickEvent)
        .join(ShortenedURL, ShortenedURL.id == ClickEvent.url_id)
        .where(ShortenedURL.user_id == owner_id)
        .where(ClickEvent.created_at >= utc_start)
        .where(ClickEvent.created_at < utc_end)
    )
    device_counts: dict[str, int] = {"desktop": 0, "mobile": 0, "tablet": 0, "unknown": 0}
    for ua in user_agent_rows:
        label = _device_label_from_user_agent(ua)
        device_counts[label] = device_counts.get(label, 0) + 1
    device_breakdown = [(label, count) for label, count in device_counts.items() if count > 0]

    previous_total_clicks: int | None = None
    click_change_percent: float | None = None
    if compare_previous:
        previous_utc_end = utc_start
        previous_utc_start = previous_utc_end - timedelta(days=days)
        previous_clicks = await db.scalar(
            select(func.count(ClickEvent.id))
            .select_from(ClickEvent)
            .join(ShortenedURL, ShortenedURL.id == ClickEvent.url_id)
            .where(ShortenedURL.user_id == owner_id)
            .where(ClickEvent.created_at >= previous_utc_start)
            .where(ClickEvent.created_at < previous_utc_end)
        )
        previous_total_clicks = int(previous_clicks or 0)
        if previous_total_clicks == 0:
            click_change_percent = 100.0 if total_clicks_int > 0 else 0.0
        else:
            click_change_percent = round(
                ((total_clicks_int - previous_total_clicks) / previous_total_clicks) * 100, 2
            )

    return (
        total_links_int,
        total_clicks_int,
        start_date,
        end_date,
        trend,
        top_links,
        top_referrers,
        device_breakdown,
        previous_total_clicks,
        click_change_percent,
    )
