"""
Admin cog - administrative commands and configuration.
"""

import datetime
import discord
from discord import app_commands
from discord.ext import commands

from bot.config import get_settings
from bot.database.connection import get_session
from bot.models.guild import GuildConfig
from bot.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class AdminCog(commands.Cog):
    """Administrative commands for bot configuration."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="setup", description="Configure support role/category/transcripts")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        support_role="Role that manages tickets",
        category="Category for new tickets",
        transcript_channel="Channel for close logs"
    )
    async def setup_command(
        self,
        interaction: discord.Interaction,
        support_role: discord.Role = None,
        category: discord.CategoryChannel = None,
        transcript_channel: discord.TextChannel = None
    ):
        """Configure bot settings."""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True
            )
        
        async with get_session() as session:
            # Get or create guild config
            guild_config = await session.get(GuildConfig, interaction.guild.id)
            if not guild_config:
                guild_config = GuildConfig(
                    id=interaction.guild.id,
                    name=interaction.guild.name
                )
                session.add(guild_config)
            
            # Update configuration
            if support_role:
                guild_config.support_role_id = support_role.id
            if category:
                guild_config.ticket_category_id = category.id
            if transcript_channel:
                guild_config.transcript_channel_id = transcript_channel.id
            
            guild_config.updated_at = datetime.datetime.now(datetime.timezone.utc)
            await session.commit()
        
        await interaction.response.send_message(
            f"✅ Configuration saved.\n"
            f"Support: {support_role.mention if support_role else '`unchanged`'}\n"
            f"Category: {category.name if category else '`unchanged`'}\n"
            f"Transcripts: {transcript_channel.mention if transcript_channel else '`unchanged`'}",
            ephemeral=True
        )
        
        logger.info(
            f"Configuration updated by {interaction.user.id} in guild {interaction.guild.id}",
            support_role=support_role.id if support_role else None,
            category=category.id if category else None,
            transcript_channel=transcript_channel.id if transcript_channel else None
        )
    
    @app_commands.command(name="autoassign", description="Configure auto-assignment (admin only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        enabled="Enable or disable auto-assignment",
        strategy="Assignment strategy (round_robin, least_loaded, specialization)"
    )
    @app_commands.choices(strategy=[
        app_commands.Choice(name="Round Robin", value="round_robin"),
        app_commands.Choice(name="Least Loaded", value="least_loaded"),
        app_commands.Choice(name="Specialization", value="specialization"),
    ])
    async def autoassign_command(
        self,
        interaction: discord.Interaction,
        enabled: bool = None,
        strategy: str = None
    ):
        """Configure auto-assignment settings."""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True
            )
        
        async with get_session() as session:
            guild_config = await session.get(GuildConfig, interaction.guild.id)
            if not guild_config:
                guild_config = GuildConfig(
                    id=interaction.guild.id,
                    name=interaction.guild.name
                )
                session.add(guild_config)
            
            if enabled is not None:
                guild_config.enable_auto_assignment = enabled
            if strategy is not None:
                guild_config.auto_assignment_strategy = strategy
            
            guild_config.updated_at = datetime.datetime.now(datetime.timezone.utc)
            await session.commit()
        
        message_parts = []
        if enabled is not None:
            message_parts.append(f"Auto-assignment: {'enabled' if enabled else 'disabled'}")
        if strategy is not None:
            message_parts.append(f"Strategy: {strategy}")
        
        await interaction.response.send_message(
            f"✅ Auto-assignment configuration updated.\n" + "\n".join(message_parts),
            ephemeral=True
        )
        
        logger.info(
            f"Auto-assignment configured by {interaction.user.id} in guild {interaction.guild.id}",
            enabled=enabled,
            strategy=strategy
        )
    
    @app_commands.command(name="staff", description="Configure staff members (admin only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        member="Staff member to configure",
        specialization="Staff specialization (e.g., billing, technical)"
    )
    async def staff_command(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        specialization: str = None
    ):
        """Configure staff member specialization."""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True
            )
        
        async with get_session() as session:
            from bot.database.repositories.user_repository import UserRepository
            
            user_repo = UserRepository(session)
            
            # Get or create user
            user = await user_repo.get_or_create_user(
                member.id,
                member.name,
                str(member.discriminator),
                member.global_name,
                str(member.avatar) if member.avatar else None
            )
            
            # Set as staff
            await user_repo.set_staff_status(user, True)
            
            # Set specialization if provided
            if specialization:
                await user_repo.set_staff_specialization(user, specialization)
            
            await session.commit()
        
        message = f"✅ {member.mention} configured as staff"
        if specialization:
            message += f" with specialization: {specialization}"
        
        await interaction.response.send_message(message, ephemeral=True)
        
        logger.info(
            f"Staff {member.id} configured with specialization {specialization} by {interaction.user.id}"
        )
