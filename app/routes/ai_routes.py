from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.models.user import User
from app.routes.auth_routes import get_optional_current_user
from app.schemas.ai import AISummarizeRequest, AISummarizeResponse
from app.services.ai_service import create_ai_insight, summarize_url

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/summarize", response_model=AISummarizeResponse)
async def summarize_link(
    payload: AISummarizeRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> AISummarizeResponse:
    try:
        summary, tags, source_mode, fallback_reason = await summarize_url(
            str(payload.original_url)
        )
        await create_ai_insight(
            db=db,
            original_url=str(payload.original_url),
            summary=summary,
            tags=tags,
            user_id=current_user.id if current_user else None,
            short_code=payload.short_code,
        )
        if source_mode.startswith("gemini:"):
            source_details = {
                "provider": "gemini",
                "model": source_mode.split(":", 1)[1],
                "fallback_used": False,
            }
        else:
            source_details = {
                "provider": "extractive",
                "model": None,
                "fallback_used": True,
                "fallback_reason": fallback_reason,
            }
        return AISummarizeResponse(
            summary=summary,
            tags=tags,
            source_mode=source_mode,
            source_details=source_details,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch and summarize the URL.",
        ) from exc
