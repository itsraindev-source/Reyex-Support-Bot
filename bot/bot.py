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
    
    # Start background tasks
    if not auto_close_loop.is_running():
        auto_close_loop.start()
        logger.info("Auto-close loop started")
    
    if not sla_monitoring_loop.is_running():
        sla_monitoring_loop.start()
        logger.info("SLA monitoring loop started")
    
    if not auto_assignment_loop.is_running():
        auto_assignment_loop.start()
        logger.info("Auto-assignment loop started")
    
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


@tasks.loop(hours=1)
async def auto_close_loop():
    """Background task to auto-close inactive tickets."""
    await bot.wait_until_ready()
    
    import io
    import datetime
    from bot.database.connection import get_session
    from bot.database.repositories.ticket_repository import TicketRepository
    from bot.database.repositories.guild_repository import GuildRepository
    from bot.models.ticket import TicketStatus
    
    try:
        async with get_session() as session:
            ticket_repo = TicketRepository(session)
            guild_repo = GuildRepository(session)
            
            # Get all guilds
            for guild in bot.guilds:
                guild_config = await guild_repo.get_guild_config(guild.id)
                if not guild_config or not guild_config.auto_close_enabled:
                    continue
                
                # Get open tickets with auto_close enabled
                from sqlalchemy import select, and_
                from bot.models.ticket import Ticket
                
                cutoff_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
                    hours=guild_config.auto_close_hours
                )
                
                query = select(Ticket).where(
                    and_(
                        Ticket.guild_id == guild.id,
                        Ticket.status == TicketStatus.OPEN,
                        Ticket.auto_close == True,
                        Ticket.last_activity < cutoff_time
                    )
                )
                
                result = await session.execute(query)
                tickets_to_close = list(result.scalars().all())
                
                for ticket in tickets_to_close:
                    try:
                        channel = guild.get_channel(ticket.channel_id)
                        if channel:
                            # Generate transcript
                            header = (
                                f"Reyex Support transcript — #{channel.name}\n"
                                f"Subject: {ticket.subject} | Type: {ticket.ticket_type} | "
                                f"Priority: {ticket.priority} | Owner: {ticket.owner_id}\n"
                                f"Exported: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n"
                                f"{'=' * 60}\n"
                            )
                            lines = [header, "Auto-closed due to inactivity"]
                            text = "\n".join(lines)
                            buf = io.BytesIO(text.encode("utf-8"))
                            transcript_file = discord.File(buf, filename=f"transcript-{channel.name}.txt")
                            
                            # Log to transcript channel
                            if guild_config.transcript_channel_id:
                                transcript_channel = guild.get_channel(guild_config.transcript_channel_id)
                                if transcript_channel:
                                    embed = discord.Embed(
                                        title=f"⏰ Auto-closed: #{channel.name}",
                                        description=f"Inactive for {guild_config.auto_close_hours}h.\nOwner: <@{ticket.owner_id}>",
                                        color=0xFEE75C,
                                        timestamp=datetime.datetime.now(datetime.timezone.utc),
                                    )
                                    await transcript_channel.send(embed=embed, file=transcript_file)
                            
                            # Close ticket
                            await ticket_repo.close_ticket(ticket, resolved=False)
                            await channel.delete(reason=f"Auto-close: {guild_config.auto_close_hours}h inactivity")
                            logger.info(f"Auto-closed ticket #{ticket.number} in guild {guild.id}")
                    except Exception as e:
                        logger.error(f"Failed to auto-close ticket #{ticket.number}: {e}")
            
            await session.commit()
    except Exception as e:
        logger.error(f"Error in auto_close_loop: {e}")


@tasks.loop(minutes=5)
async def sla_monitoring_loop():
    """Background task to monitor SLA compliance and send alerts."""
    await bot.wait_until_ready()
    
    import datetime
    from bot.database.connection import get_session
    from bot.database.repositories.ticket_repository import TicketRepository
    from bot.database.repositories.guild_repository import GuildRepository
    from bot.services.sla_service import get_sla_service
    from bot.models.ticket import TicketStatus
    
    try:
        sla_service = get_sla_service()
        
        async with get_session() as session:
            ticket_repo = TicketRepository(session)
            guild_repo = GuildRepository(session)
            
            # Get all guilds
            for guild in bot.guilds:
                guild_config = await guild_repo.get_guild_config(guild.id)
                if not guild_config or not guild_config.enable_automation:
                    continue
                
                # Check SLA compliance
                breaches = await sla_service.check_sla_compliance(guild.id)
                
                # Send alerts for breaches
                if breaches and guild_config.support_role_id:
                    support_role = guild.get_role(guild_config.support_role_id)
                    if support_role:
                        for breach in breaches:
                            try:
                                # Get the ticket to find the channel
                                ticket = await ticket_repo.get_ticket_by_id(breach["ticket_id"])
                                if ticket:
                                    channel = guild.get_channel(ticket.channel_id)
                                    if channel:
                                        embed = discord.Embed(
                                            title="⚠️ SLA Breach Alert",
                                            description=(
                                                f"Ticket #{breach['ticket_number']} has breached SLA for {breach['event_type']}\n"
                                                f"Priority: {breach['priority']}\n"
                                                f"Target time: {breach['target_time']}"
                                            ),
                                            color=0xED4245,
                                            timestamp=datetime.datetime.now(datetime.timezone.utc),
                                        )
                                        await channel.send(content=f"{support_role.mention}", embed=embed)
                                        logger.info(f"SLA breach alert sent for ticket #{breach['ticket_number']}")
                            except Exception as e:
                                logger.error(f"Failed to send SLA breach alert: {e}")
    
    except Exception as e:
        logger.error(f"Error in sla_monitoring_loop: {e}")


@tasks.loop(minutes=2)
async def auto_assignment_loop():
    """Background task to auto-assign unclaimed tickets."""
    await bot.wait_until_ready()
    
    from bot.database.connection import get_session
    from bot.database.repositories.ticket_repository import TicketRepository
    from bot.database.repositories.guild_repository import GuildRepository
    from bot.services.assignment_service import get_assignment_service
    from bot.models.ticket import TicketStatus
    
    try:
        assignment_service = get_assignment_service()
        
        async with get_session() as session:
            ticket_repo = TicketRepository(session)
            guild_repo = GuildRepository(session)
            
            # Get all guilds
            for guild in bot.guilds:
                guild_config = await guild_repo.get_guild_config(guild.id)
                if not guild_config or not guild_config.enable_auto_assignment:
                    continue
                
                # Get unclaimed tickets
                from sqlalchemy import select, and_
                from bot.models.ticket import Ticket
                
                query = select(Ticket).where(
                    and_(
                        Ticket.guild_id == guild.id,
                        Ticket.status == TicketStatus.OPEN,
                        Ticket.claimed_by.is_(None)
                    )
                ).order_by(Ticket.created_at.asc())
                
                result = await session.execute(query)
                unclaimed_tickets = list(result.scalars().all())
                
                for ticket in unclaimed_tickets:
                    try:
                        # Auto-assign the ticket
                        staff_id = await assignment_service.auto_assign_ticket(
                            ticket,
                            strategy=guild_config.auto_assignment_strategy,
                            specialization=ticket.ticket_type
                        )
                        
                        if staff_id:
                            # Refresh ticket embed
                            channel = guild.get_channel(ticket.channel_id)
                            if channel:
                                cog = bot.get_cog("TicketsCog")
                                if cog:
                                    await cog._refresh_ticket_embed(channel, ticket)
                            
                            # Notify staff
                            staff_member = guild.get_member(staff_id)
                            if staff_member:
                                try:
                                    await staff_member.send(
                                        f"🎫 You've been auto-assigned ticket #{ticket.number}: {ticket.subject}"
                                    )
                                except Exception:
                                    pass
                            
                            logger.info(f"Auto-assigned ticket #{ticket.number} to {staff_id}")
                    
                    except Exception as e:
                        logger.error(f"Failed to auto-assign ticket #{ticket.number}: {e}")
    
    except Exception as e:
        logger.error(f"Error in auto_assignment_loop: {e}")


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

    tickets_cog = tickets.TicketsCog(bot)
    await bot.add_cog(tickets_cog)
    await bot.add_cog(admin.AdminCog(bot))
    await bot.add_cog(automation.AutomationCog(bot))
    await bot.add_cog(translation.TranslationCog(bot))

    # Register persistent views
    bot.add_view(tickets.TicketPanelView())
    bot.add_view(tickets.TicketControlView())


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
