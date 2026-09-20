"""
Ticket database models.
"""

import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.connection import Base


class TicketStatus(str, Enum):
    """Ticket status enumeration."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_USER = "waiting_for_user"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    """Ticket priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Ticket(Base):
    """
    Ticket model representing a support ticket.
    """
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    
    # Discord identifiers
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    channel_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Ticket details
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    ticket_type: Mapped[str] = mapped_column(String(50), nullable=False, default="general")
    
    # Status and priority
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TicketStatus.OPEN.value,
        index=True
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TicketPriority.MEDIUM.value,
        index=True
    )
    
    # Assignment
    claimed_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Channel management
    category_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    channel_name: Mapped[str] = mapped_column(String(100), nullable=True)
    
    # Automation flags
    auto_close: Mapped[bool] = mapped_column(Boolean, default=False)
    need_human: Mapped[bool] = mapped_column(Boolean, default=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Activity tracking
    last_activity: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )
    first_response_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        onupdate=datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )
    
    # Additional metadata (JSON for flexibility)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Relationships
    claimer: Mapped["User"] = relationship("User", back_populates="claimed_tickets", foreign_keys=[claimed_by])
    messages: Mapped[list["TicketMessage"]] = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")
    sla_events: Mapped[list["SLAEvent"]] = relationship("SLAEvent", back_populates="ticket", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, number={self.number}, subject='{self.subject}', status={self.status})>"


class TicketMessage(Base):
    """
    Ticket message model for storing message history and analytics.
    """
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    
    # Message details
    message_id: Mapped[int] = mapped_column(Integer, nullable=False)  # Discord message ID
    author_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    author_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user', 'staff', 'bot'
    content: Mapped[str] = mapped_column(Text, nullable=True)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Attachments (store URLs)
    attachments: Mapped[list[str]] = mapped_column(JSON, default=list)
    
    # Timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
        index=True
    )
    
    # Relationships
    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="messages")
    
    def __repr__(self) -> str:
        return f"<TicketMessage(id={self.id}, ticket_id={self.ticket_id}, author_id={self.author_id})>"


class SLAEvent(Base):
    """
    SLA event model for tracking SLA compliance and breaches.
    """
    __tablename__ = "sla_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    
    # Event details
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'first_response', 'resolution', 'follow_up'
    target_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    target_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # 'pending', 'met', 'breached'
    breached: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False
    )
    
    # Relationships
    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="sla_events")
    
    def __repr__(self) -> str:
        return f"<SLAEvent(id={self.id}, ticket_id={self.ticket_id}, event_type={self.event_type}, status={self.status})>"
