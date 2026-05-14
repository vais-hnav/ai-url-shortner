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
    short_url: str | None = None
    created_at: datetime
    ai_summary: str | None = None
    ai_tags: list[str] = Field(default_factory=list)
    ai_source_mode: str | None = None
    total_clicks: int = 0


class URLDetailsResponse(BaseModel):
    id: int
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    total_clicks: int
    ai_summary: str | None = None
    ai_tags: list[str] = Field(default_factory=list)
    ai_last_updated_at: datetime | None = None


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
    recent_clicks_limit: int
    recent_clicks: list[ClickEventResponse]
    top_referrers: list["LabelCount"]
    device_breakdown: list["LabelCount"]


class DailyClickCount(BaseModel):
    date: date
    clicks: int


class LabelCount(BaseModel):
    label: str
    clicks: int


class URLDailyAnalyticsResponse(BaseModel):
    short_code: str
    days: int
    timezone_offset_minutes: int
    start_date: date
    end_date: date
    daily_clicks: list[DailyClickCount]


class UserURLListResponse(BaseModel):
    total_count: int
    limit: int
    offset: int
    has_more: bool
    next_offset: int | None
    items: list[URLResponse]


class OverviewTrendPoint(BaseModel):
    date: date
    clicks: int


class UserAnalyticsOverviewResponse(BaseModel):
    total_links: int
    total_clicks: int
    active_links: int = 0
    average_clicks_per_active_link: float = 0.0
    top_link_share_percent: float = 0.0
    direct_traffic_share_percent: float = 0.0
    best_day: date | None = None
    best_day_clicks: int = 0
    previous_total_clicks: int | None = None
    click_change_percent: float | None = None
    window_days: int
    timezone_offset_minutes: int
    start_date: date
    end_date: date
    trend: list[OverviewTrendPoint]
    hourly_distribution: list[LabelCount]
    weekday_distribution: list[LabelCount]
    top_links: list["TopLinkPerformance"]
    top_referrers: list[LabelCount]
    device_breakdown: list[LabelCount]


class TopLinkPerformance(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    clicks: int
