"""
Automation database models for SLA rules, canned responses, and escalation.
"""

import datetime
from typing import Optional, List

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.connection import Base


class SLARule(Base):
    """
    SLA (Service Level Agreement) rule model for defining response and resolution targets.
    """
    __tablename__ = "sla_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Rule details
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Priority matching
    priority: Mapped[str] = mapped_column(String(20), nullable=False)  # 'low', 'medium', 'high', 'urgent'
    ticket_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Optional type filter
    
    # Time targets (in minutes)
    first_response_target: Mapped[int] = mapped_column(Integer, nullable=False)  # Target for first staff response
    resolution_target: Mapped[int] = mapped_column(Integer, nullable=False)  # Target for ticket resolution
    follow_up_target: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Target for follow-up responses
    
    # Alert settings
    alert_before_breach: Mapped[int] = mapped_column(Integer, default=15)  # Alert X minutes before breach
    alert_channel_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Channel for breach alerts
    alert_role_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Role to ping on breach
    
    # Business hours (optional)
    business_hours_only: Mapped[bool] = mapped_column(Boolean, default=False)
    business_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # "09:00"
    business_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)  # "17:00"
    business_days: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)  # ["mon", "tue", "wed", "thu", "fri"]
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
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
        return f"<SLARule(id={self.id}, name='{self.name}', priority={self.priority})>"


class CannedResponse(Base):
    """
    Canned response model for pre-written support responses.
    """
    __tablename__ = "canned_responses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Response details
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Organization
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    
    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Permissions
    required_role_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Role required to use
    
    # Permissions
    required_role_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Role required to use
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Timestamps
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)  # Discord user ID
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
        return f"<CannedResponse(id={self.id}, name='{self.name}', category='{self.category}')>"
    
    def increment_usage(self):
        """Increment the usage counter and update last used timestamp."""
        self.usage_count += 1
        self.last_used_at = datetime.datetime.now(datetime.timezone.utc)


class EscalationRule(Base):
    """
    Escalation rule model for automatic ticket escalation based on conditions.
    """
    __tablename__ = "escalation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Rule details
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Trigger conditions
    condition_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'time_unclaimed', 'time_since_last_response', 'priority', 'custom'
    condition_value: Mapped[dict] = mapped_column(JSON, nullable=False)  # Condition-specific values
    
    # Priority filter (optional)
    priority_filter: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)  # ["high", "urgent"]
    
    # Escalation actions
    actions: Mapped[list[dict]] = mapped_column(JSON, nullable=False)  # List of actions to take
    # Example actions:
    # [
    #   {"type": "ping_role", "role_id": 123456789},
    #   {"type": "dm_user", "user_id": 987654321, "message": "Ticket escalated"},
    #   {"type": "change_priority", "priority": "urgent"},
    #   {"type": "reassign", "role_id": 123456789}
    # ]
    
    # Escalation chain (for multi-level escalation)
    escalation_level: Mapped[int] = mapped_column(Integer, default=1)
    max_escalations: Mapped[int] = mapped_column(Integer, default=3)
    
    # Cooldown to prevent repeated escalations
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=60)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
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
        return f"<EscalationRule(id={self.id}, name='{self.name}', condition_type={self.condition_type})>"


class AutomationLog(Base):
    """
    Automation log model for tracking all automation actions.
    """
    __tablename__ = "automation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ticket_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    # Action details
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'sla_breach', 'escalation', 'auto_assign', etc.
    rule_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Reference to the rule that triggered
    rule_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Action details
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Context
    triggered_by: Mapped[str] = mapped_column(String(50), nullable=False)  # 'system', 'user', 'manual'
    triggered_by_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # User ID if applicable
    
    # Timestamps
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
        index=True
    )
    
    def __repr__(self) -> str:
        return f"<AutomationLog(id={self.id}, action_type='{self.action_type}', success={self.success})>"
