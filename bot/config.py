"""
Configuration management using Pydantic settings.
Environment variables and configuration validation.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Discord Configuration
    discord_token: str = Field(..., description="Discord bot token")
    discord_client_id: str = Field(..., description="Discord application client ID")
    support_role_id: Optional[int] = Field(default=None, description="Support role ID")
    admin_role_id: Optional[int] = Field(default=None, description="Admin role ID")
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql://reyex:reyex@localhost:5432/reyex_support",
        description="PostgreSQL connection string"
    )
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    
    # Bot Configuration
    bot_name: str = Field(default="Reyex Support", description="Bot display name")
    brand_color: int = Field(default=0x5865F2, description="Brand color for embeds")
    ticket_prefix: str = Field(default="ticket-", description="Ticket channel name prefix")
    max_open_tickets_per_user: int = Field(default=3, description="Max concurrent tickets per user")
    
    # Feature Flags
    enable_translation: bool = Field(default=True, description="Enable auto-translation feature")
    enable_automation: bool = Field(default=True, description="Enable automation features")
    enable_web_dashboard: bool = Field(default=True, description="Enable web dashboard")
    
    # Translation Configuration
    libretranslate_url: str = Field(
        default="https://libretranslate.de",
        description="LibreTranslate API URL"
    )
    libretranslate_api_key: Optional[str] = Field(
        default=None,
        description="LibreTranslate API key (if using paid instance)"
    )
    
    # Monitoring & Error Tracking
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Web Dashboard Configuration
    web_api_host: str = Field(default="0.0.0.0", description="Web API host")
    web_api_port: int = Field(default=8000, description="Web API port")
    web_dashboard_url: Optional[str] = Field(
        default=None,
        description="Public URL of web dashboard for OAuth callbacks"
    )
    discord_oauth_client_id: Optional[str] = Field(
        default=None,
        description="Discord OAuth2 client ID for web dashboard"
    )
    discord_oauth_client_secret: Optional[str] = Field(
        default=None,
        description="Discord OAuth2 client secret for web dashboard"
    )
    
    # SLA Configuration (default values)
    sla_first_response_urgent: int = Field(default=15, description="SLA first response for urgent (minutes)")
    sla_first_response_high: int = Field(default=30, description="SLA first response for high (minutes)")
    sla_first_response_medium: int = Field(default=60, description="SLA first response for medium (minutes)")
    sla_first_response_low: int = Field(default=120, description="SLA first response for low (minutes)")
    
    sla_resolution_urgent: int = Field(default=240, description="SLA resolution for urgent (minutes)")
    sla_resolution_high: int = Field(default=480, description="SLA resolution for high (minutes)")
    sla_resolution_medium: int = Field(default=1440, description="SLA resolution for medium (minutes)")
    sla_resolution_low: int = Field(default=2880, description="SLA resolution for low (minutes)")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the standard Python logging levels."""
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    @field_validator('brand_color')
    @classmethod
    def validate_brand_color(cls, v: int) -> int:
        """Validate brand color is a valid hex color."""
        if not 0 <= v <= 0xFFFFFF:
            raise ValueError('brand_color must be a valid hex color (0x000000 to 0xFFFFFF)')
        return v


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
