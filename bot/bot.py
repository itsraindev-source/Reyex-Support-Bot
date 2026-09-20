"""
Main Discord bot client initialization and setup.
"""

import asyncio
from typing import Optional

import discord
from discord.ext import commands, tasks

from bot.config import get_settings
from bot.database.connection import close_db, init_db
from bot.database.redis_client import close_redis
from bot.utils.logger import get_logger, setup_logger

# Setup logging
setup_logger()
logger = get_logger(__name__)

# Get settings
settings = get_settings()

# Discord intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.presences = False

# Create bot instance
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    activity=discord.Activity(
        type=discord.ActivityType.watching,
        name="for /help"
    )
)


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guilds")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Load cogs
    try:
        await load_cogs()
        logger.info("All cogs loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load cogs: {e}")
        raise
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} global slash commands")
        
        # Per-guild sync for immediate updates
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                g_synced = await bot.tree.sync(guild=guild)
                logger.info(f"Synced {len(g_synced)} commands to guild {guild.name} ({guild.id})")
            except Exception as e:
                logger.warning(f"Failed to sync commands to guild {guild.id}: {e}")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")
    
    logger.info("Bot is ready!")


@bot.event
async def on_guild_join(guild: discord.Guild):
    """Called when the bot joins a guild."""
    logger.info(f"Joined guild: {guild.name} (ID: {guild.id})")
    
    # Sync commands to the new guild
    try:
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        logger.info(f"Synced {len(synced)} commands to new guild {guild.name}")
    except Exception as e:
        logger.error(f"Failed to sync commands to new guild {guild.id}: {e}")


@bot.event
async def on_guild_remove(guild: discord.Guild):
    """Called when the bot leaves a guild."""
    logger.info(f"Left guild: {guild.name} (ID: {guild.id})")


@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: Exception):
    """Called when an application command error occurs."""
    logger.error(
        f"Application command error: {error}",
        command=interaction.command.name if interaction.command else "unknown",
        user=interaction.user.id,
        guild=interaction.guild.id if interaction.guild else None,
    )
    
    # Send error message to user if possible
    if interaction.response.is_done():
        try:
            await interaction.followup.send(
                "An error occurred while executing this command. Please try again later.",
                ephemeral=True
            )
        except Exception:
            pass
    else:
        try:
            await interaction.response.send_message(
                "An error occurred while executing this command. Please try again later.",
                ephemeral=True
            )
        except Exception:
            pass


async def load_cogs():
    """Load all bot cogs."""
    # Import cogs here to avoid circular imports
    from bot.cogs import tickets, admin, automation, translation
    
    await bot.add_cog(tickets.TicketsCog(bot))
    await bot.add_cog(admin.AdminCog(bot))
    await bot.add_cog(automation.AutomationCog(bot))
    await bot.add_cog(translation.TranslationCog(bot))


async def cleanup():
    """Cleanup resources before shutdown."""
    logger.info("Starting cleanup...")
    
    # Close database connection
    try:
        await close_db()
        logger.info("Database connection closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")
    
    # Close Redis connection
    try:
        await close_redis()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")
    
    logger.info("Cleanup complete")


def run_bot():
    """Run the Discord bot."""
    try:
        bot.run(settings.discord_token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error running bot: {e}")
        raise
    finally:
        # Run cleanup
        asyncio.run(cleanup())


if __name__ == "__main__":
    run_bot()
