"""
User database models.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.connection import Base


class User(Base):
    """
    User model representing Discord users who interact with the bot.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Discord user ID
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    discriminator: Mapped[str] = mapped_column(String(10), nullable=True)  # Old discriminator or "0"
    global_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Display name
    avatar: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Language preferences
    language: Mapped[str] = mapped_column(String(10), default="en")  # ISO language code
    auto_translate: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # User statistics
    tickets_created: Mapped[int] = mapped_column(Integer, default=0)
    tickets_closed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Staff-specific fields
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    staff_specialization: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., 'billing', 'technical'
    
    # Staff performance metrics
    tickets_claimed: Mapped[int] = mapped_column(Integer, default=0)
    tickets_resolved: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_time_seconds: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)
    total_response_time_seconds: Mapped[int] = mapped_column(Integer, default=0)
    
    # User preferences and metadata
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
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
    last_seen_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )
    
    # Relationships
    claimed_tickets: Mapped[List["Ticket"]] = relationship("Ticket", back_populates="claimer", foreign_keys="Ticket.claimed_by")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', is_staff={self.is_staff})>"
    
    @property
    def display_name(self) -> str:
        """Get the best available display name for the user."""
        if self.global_name:
            return self.global_name
        if self.username:
            if self.discriminator and self.discriminator != "0":
                return f"{self.username}#{self.discriminator}"
            return self.username
        return f"User {self.id}"
    
    def increment_tickets_created(self):
        """Increment the tickets created counter."""
        self.tickets_created += 1
    
    def increment_tickets_closed(self):
        """Increment the tickets closed counter."""
        self.tickets_closed += 1
    
    def increment_tickets_claimed(self):
        """Increment the tickets claimed counter (staff only)."""
        if self.is_staff:
            self.tickets_claimed += 1
    
    def increment_tickets_resolved(self):
        """Increment the tickets resolved counter (staff only)."""
        if self.is_staff:
            self.tickets_resolved += 1
    
    def update_response_time(self, response_seconds: int):
        """Update response time statistics (staff only)."""
        if self.is_staff:
            self.total_response_time_seconds += response_seconds
            if self.tickets_claimed > 0:
                self.avg_response_time_seconds = self.total_response_time_seconds / self.tickets_claimed