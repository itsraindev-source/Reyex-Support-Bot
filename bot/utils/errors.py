"""
Error handling utilities and custom exceptions.
"""

import functools
import inspect
import traceback
from typing import Any, Callable, Optional, TypeVar

from loguru import logger

F = TypeVar('F', bound=Callable[..., Any])


class ReyexError(Exception):
    """Base exception for Reyex Support Bot errors."""
    
    def __init__(self, message: str, *, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseError(ReyexError):
    """Database-related errors."""
    pass


class TicketError(ReyexError):
    """Ticket-related errors."""
    pass


class UserError(ReyexError):
    """User-related errors."""
    pass


class PermissionError(ReyexError):
    """Permission-related errors."""
    pass


class ConfigurationError(ReyexError):
    """Configuration-related errors."""
    pass


class ExternalServiceError(ReyexError):
    """External service (translation, etc.) errors."""
    pass


def handle_errors(
    *,
    reraise: bool = False,
    default_return: Any = None,
    log_level: str = "ERROR",
    context: Optional[dict] = None,
):
    """
    Decorator for handling errors with logging and optional context.
    
    Args:
        reraise: Whether to re-raise the exception after handling
        default_return: Value to return if an error occurs and not re-raising
        log_level: Log level to use for errors
        context: Additional context to include in error logs
        
    Example:
        @handle_errors(reraise=False, default_return=None)
        async def my_function():
            # This will catch and log errors without raising
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                if context:
                    error_context.update(context)
                
                log_func = getattr(logger, log_level.lower(), logger.error)
                log_func(
                    f"Error in {func.__name__}: {e}",
                    **error_context
                )
                
                logger.debug(f"Traceback: {traceback.format_exc()}")
                
                if reraise:
                    raise
                return default_return
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = {
                    "function": func.__name__,
                    "module": func.__module__,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                if context:
                    error_context.update(context)
                
                log_func = getattr(logger, log_level.lower(), logger.error)
                log_func(
                    f"Error in {func.__name__}: {e}",
                    **error_context
                )
                
                logger.debug(f"Traceback: {traceback.format_exc()}")
                
                if reraise:
                    raise
                return default_return
        
        # Check if function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore
    
    return decorator


def safe_execute(
    func: Callable,
    *args,
    default_return: Any = None,
    log_error: bool = True,
    **kwargs
) -> Any:
    """
    Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        default_return: Value to return if an error occurs
        log_error: Whether to log errors
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function result or default_return if error occurs
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(
                f"Error executing {func.__name__}: {e}",
                function=func.__name__,
                error_type=type(e).__name__,
            )
            logger.debug(f"Traceback: {traceback.format_exc()}")
        return default_return


def safe_execute_async(
    func: Callable,
    *args,
    default_return: Any = None,
    log_error: bool = True,
    **kwargs
) -> Any:
    """
    Safely execute an async function with error handling.
    
    Args:
        func: Async function to execute
        *args: Positional arguments for the function
        default_return: Value to return if an error occurs
        log_error: Whether to log errors
        **kwargs: Keyword arguments for the function
        
    Returns:
        Coroutine that resolves to function result or default_return if error occurs
    """
    async def wrapper():
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if log_error:
                logger.error(
                    f"Error executing {func.__name__}: {e}",
                    function=func.__name__,
                    error_type=type(e).__name__,
                )
                logger.debug(f"Traceback: {traceback.format_exc()}")
            return default_return
    
    return wrapper()
