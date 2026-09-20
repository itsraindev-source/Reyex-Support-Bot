"""Database models module."""

from bot.database.connection import Base
from bot.models.ticket import Ticket, TicketMessage, SLAEvent, TicketStatus, TicketPriority
from bot.models.user import User
from bot.models.automation import SLARule, CannedResponse, EscalationRule, AutomationLog

__all__ = [
    "Base",
    "Ticket",
    "TicketMessage", 
    "SLAEvent",
    "TicketStatus",
    "TicketPriority",
    "User",
    "SLARule",
    "CannedResponse",
    "EscalationRule",
    "AutomationLog",
]
