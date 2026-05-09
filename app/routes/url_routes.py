from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.schemas.url import URLCreate, URLResponse
from app.services.url_service import create_shortened_url, get_shortened_url_by_code

router = APIRouter(prefix="/urls", tags=["urls"])


@router.post("", response_model=URLResponse, status_code=status.HTTP_201_CREATED)
async def create_url(
    payload: URLCreate, db: AsyncSession = Depends(get_db_session)
) -> URLResponse:
    try:
        created = await create_shortened_url(db=db, original_url=str(payload.original_url))
        return URLResponse.model_validate(created)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.get("/{short_code}", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def redirect_to_original_url(
    short_code: str, db: AsyncSession = Depends(get_db_session)
) -> RedirectResponse:
    shortened_url = await get_shortened_url_by_code(db=db, short_code=short_code)
    if not shortened_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found."
        )

    return RedirectResponse(url=shortened_url.original_url, status_code=307)
