"""Utility functions module."""

from bot.utils.embeds import (
    build_panel_embed,
    build_welcome_embed,
    build_error_embed,
    build_success_embed,
    build_info_embed,
    build_warning_embed,
)
from bot.utils.logger import get_logger, setup_logger
from bot.utils.permissions import is_staff, is_admin, has_permission, can_manage_ticket, can_close_ticket
from bot.utils.errors import (
    ReyexError,
    DatabaseError,
    TicketError,
    UserError,
    PermissionError,
    ConfigurationError,
    ExternalServiceError,
    handle_errors,
    safe_execute,
    safe_execute_async,
)

__all__ = [
    "build_panel_embed",
    "build_welcome_embed",
    "build_error_embed",
    "build_success_embed",
    "build_info_embed",
    "build_warning_embed",
    "get_logger",
    "setup_logger",
    "is_staff",
    "is_admin",
    "has_permission",
    "can_manage_ticket",
    "can_close_ticket",
    "ReyexError",
    "DatabaseError",
    "TicketError",
    "UserError",
    "PermissionError",
    "ConfigurationError",
    "ExternalServiceError",
    "handle_errors",
    "safe_execute",
    "safe_execute_async",
]
