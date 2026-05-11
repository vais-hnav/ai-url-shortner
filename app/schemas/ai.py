from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class AISummarizeRequest(BaseModel):
    original_url: HttpUrl
    short_code: str | None = Field(default=None, min_length=3, max_length=64)


class AISummarizeResponse(BaseModel):
    summary: str
    tags: list[str]
    source_mode: str
    source_details: dict


class AIInsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    url_id: int | None
    original_url: str
    summary: str
    tags: list[str]
    created_at: datetime
