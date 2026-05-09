from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class URLCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: str | None = Field(default=None, min_length=3, max_length=32)


class URLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
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


class DailyClickCount(BaseModel):
    date: date
    clicks: int


class URLDailyAnalyticsResponse(BaseModel):
    short_code: str
    days: int
    daily_clicks: list[DailyClickCount]


class UserURLListResponse(BaseModel):
    total_count: int
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None
    items: list[URLResponse]
