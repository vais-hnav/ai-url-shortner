from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


class ClickEvent(Base):
    __tablename__ = "click_events"

    id = Column(Integer, primary_key=True)
    url_id = Column(Integer, ForeignKey("shortened_urls.id"), nullable=False, index=True)
    referrer = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    url = relationship("ShortenedURL", back_populates="click_events")
