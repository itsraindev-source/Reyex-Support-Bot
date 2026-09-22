"""
Guild database models.
"""

import datetime
from typing import Optional, List

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.connection import Base


class GuildConfig(Base):
    """
    Guild configuration model for per-server settings.
    """
    __tablename__ = "guild_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Discord guild ID
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Role IDs
    support_role_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    admin_role_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Channel IDs
    ticket_category_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transcript_channel_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Bot settings
    max_open_tickets_per_user: Mapped[int] = mapped_column(Integer, default=3)
    ticket_prefix: Mapped[str] = mapped_column(String(20), default="ticket-")
    
    # Feature flags
    enable_translation: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_automation: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_auto_assignment: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_assignment_strategy: Mapped[str] = mapped_column(String(50), default="round_robin")
    
    # Auto-assignment settings
    auto_close_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_close_hours: Mapped[int] = mapped_column(Integer, default=24)
    
    # Ticket types configuration (JSON)
    ticket_types: Mapped[dict] = mapped_column(JSON, default=dict)
    disabled_ticket_types: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        onupdate=datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<GuildConfig(id={self.id}, name='{self.name}')>"
