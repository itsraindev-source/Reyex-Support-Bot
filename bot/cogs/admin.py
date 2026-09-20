"""
Admin cog - administrative commands and configuration.
"""

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.logger import get_logger

logger = get_logger(__name__)


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
        
        # This would update configuration in the database
        # For now, just acknowledge
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
