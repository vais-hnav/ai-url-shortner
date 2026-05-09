from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class URLCreate(BaseModel):
    original_url: HttpUrl


class URLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_url: str
    short_code: str
    created_at: datetime


class ClickEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    referrer: str | None
    user_agent: str | None
    ip_address: str | None
    created_at: datetime


class URLAnalyticsResponse(BaseModel):
    short_code: str
    total_clicks: int
    recent_clicks: list[ClickEventResponse]
