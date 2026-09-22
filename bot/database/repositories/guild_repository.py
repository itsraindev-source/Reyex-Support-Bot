"""
Guild repository for database operations.
"""

import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.guild import GuildConfig
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class GuildRepository:
    """Repository for guild-related database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_guild_config(self, guild_id: int) -> Optional[GuildConfig]:
        """Get guild configuration by ID."""
        return await self.session.get(GuildConfig, guild_id)
    
    async def get_or_create_guild_config(self, guild_id: int, guild_name: str) -> GuildConfig:
        """Get existing guild config or create new one."""
        guild_config = await self.get_guild_config(guild_id)
        
        if guild_config is None:
            guild_config = GuildConfig(
                id=guild_id,
                name=guild_name
            )
            self.session.add(guild_config)
            await self.session.flush()
            await self.session.refresh(guild_config)
            logger.info(f"Created guild config for {guild_id} ({guild_name})")
        
        return guild_config
    
    async def update_guild_config(self, guild_config: GuildConfig) -> GuildConfig:
        """Update guild configuration."""
        guild_config.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await self.session.flush()
        await self.session.refresh(guild_config)
        return guild_config
