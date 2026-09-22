"""
Model registry to ensure all models are imported and registered with SQLAlchemy.
This file should be imported before using the database to ensure all models are available.
"""

# Import all models to register them with SQLAlchemy
from bot.models.ticket import Ticket, TicketMessage, SLAEvent
from bot.models.user import User
from bot.models.guild import GuildConfig
from bot.models.automation import SLARule, CannedResponse, EscalationRule, AutomationLog

__all__ = [
    "Ticket",
    "TicketMessage",
    "SLAEvent",
    "User",
    "GuildConfig",
    "SLARule",
    "CannedResponse",
    "EscalationRule",
    "AutomationLog",
]
