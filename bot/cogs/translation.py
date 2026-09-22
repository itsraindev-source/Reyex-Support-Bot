"""
Translation cog - auto-translation functionality.
"""

import discord
from discord import app_commands
from discord.ext import commands

from bot.database.connection import get_session
from bot.database.repositories.user_repository import UserRepository
from bot.services.translation_service import get_translation_service
from bot.utils.logger import get_logger

logger = get_logger(__name__)


class TranslationCog(commands.Cog):
    """Translation features for multi-language support."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.translation_service = get_translation_service()
        logger.info("TranslationCog loaded")
    
    @app_commands.command(name="language", description="Set your language preference")
    @app_commands.describe(language="Language code (e.g., en, es, fr)")
    async def language_command(self, interaction: discord.Interaction, language: str):
        """Set language preference for auto-translation."""
        supported = await self.translation_service.get_supported_languages()
        
        if language not in supported:
            supported_list = ", ".join(supported.keys())
            return await interaction.response.send_message(
                f"Unsupported language. Supported languages: {supported_list}",
                ephemeral=True
            )
        
        # Update user's language preference in database
        async with get_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create_user(
                interaction.user.id,
                interaction.user.name,
                str(interaction.user.discriminator),
                interaction.user.global_name,
                str(interaction.user.avatar) if interaction.user.avatar else None
            )
            await user_repo.set_language_preference(user, language)
        
        await interaction.response.send_message(
            f"✅ Language preference set to {supported[language]} ({language})",
            ephemeral=True
        )
        
        logger.info(f"User {interaction.user.id} set language preference to {language}")
    
    @app_commands.command(name="autotranslate", description="Enable/disable auto-translation")
    @app_commands.describe(enabled="Whether to enable auto-translation")
    async def autotranslate_command(self, interaction: discord.Interaction, enabled: bool):
        """Enable or disable auto-translation."""
        async with get_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create_user(
                interaction.user.id,
                interaction.user.name,
                str(interaction.user.discriminator),
                interaction.user.global_name,
                str(interaction.user.avatar) if interaction.user.avatar else None
            )
            user.auto_translate = enabled
            await user_repo.update_user(user)
        
        status = "enabled" if enabled else "disabled"
        await interaction.response.send_message(
            f"✅ Auto-translation {status}",
            ephemeral=True
        )
        
        logger.info(f"User {interaction.user.id} {status} auto-translation")
    
    @app_commands.command(name="translate", description="Translate text manually")
    @app_commands.describe(text="Text to translate", target_language="Target language code")
    async def translate_command(
        self,
        interaction: discord.Interaction,
        text: str,
        target_language: str
    ):
        """Manually translate text."""
        await interaction.response.defer(ephemeral=True)
        
        translated = await self.translation_service.translate_text(text, target_language)
        
        if translated:
            await interaction.followup.send(
                f"**Original:** {text}\n**Translated:** {translated}",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "Translation failed. Please check the language code and try again.",
                ephemeral=True
            )
    
    @app_commands.command(name="languages", description="List supported languages")
    async def languages_command(self, interaction: discord.Interaction):
        """List supported languages."""
        supported = await self.translation_service.get_supported_languages()
        
        language_list = "\n".join(
            f"**{code}**: {name}" for code, name in supported.items()
        )
        
        embed = discord.Embed(
            title="Supported Languages",
            description=language_list,
            color=0x5865F2,
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
