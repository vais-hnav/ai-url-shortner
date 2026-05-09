import secrets
import string

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import ShortenedURL

ALPHABET = string.ascii_letters + string.digits
SHORT_CODE_LENGTH = 7
MAX_GENERATION_ATTEMPTS = 10


def _generate_short_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(SHORT_CODE_LENGTH))


async def create_shortened_url(db: AsyncSession, original_url: str) -> ShortenedURL:
    for _ in range(MAX_GENERATION_ATTEMPTS):
        short_code = _generate_short_code()
        existing = await db.scalar(
            select(ShortenedURL).where(ShortenedURL.short_code == short_code)
        )
        if existing:
            continue

        shortened_url = ShortenedURL(original_url=original_url, short_code=short_code)
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
