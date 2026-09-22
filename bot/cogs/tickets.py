"""
Ticket management cog - core ticket functionality.
"""

import asyncio
import datetime
import io
import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import and_

from bot.config import get_settings
from bot.database.connection import get_session
from bot.models.ticket import Ticket, TicketMessage, TicketStatus, TicketPriority
from bot.models.user import User
from bot.utils.embeds import build_panel_embed, build_welcome_embed
from bot.utils.logger import get_logger
from bot.utils.permissions import is_staff

logger = get_logger(__name__)

settings = get_settings()
DIVIDER = "─────────────────────────────"


class TicketsCog(commands.Cog):
    """Ticket management commands and events."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.brand_color = settings.brand_color
        self.ticket_prefix = settings.ticket_prefix
        self.max_open_tickets = settings.max_open_tickets_per_user
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Track messages in ticket channels and handle auto-translation."""
        if message.author.bot or not message.guild:
            return
        
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            from bot.database.repositories.user_repository import UserRepository
            from bot.database.repositories.guild_repository import GuildRepository
            from bot.services.translation_service import get_translation_service
            
            ticket_repo = TicketRepository(session)
            user_repo = UserRepository(session)
            guild_repo = GuildRepository(session)
            
            # Check if this is a ticket channel
            ticket = await ticket_repo.get_ticket_by_channel_id(message.channel.id)
            if not ticket:
                return
            
            # Track message in database
            author_type = "staff" if is_staff(message.author) else "user"
            attachments = [a.url for a in message.attachments] if message.attachments else None
            
            await ticket_repo.add_ticket_message(
                ticket_id=ticket.id,
                message_id=message.id,
                author_id=message.author.id,
                author_type=author_type,
                content=message.content,
                is_staff=is_staff(message.author),
                attachments=attachments
            )
            
            # Update ticket activity
            ticket.last_activity = datetime.datetime.now(datetime.timezone.utc)
            await ticket_repo.update_ticket(ticket)
            
            # Update user last seen
            user = await user_repo.get_or_create_user(
                message.author.id,
                message.author.name,
                str(message.author.discriminator),
                message.author.global_name,
                str(message.author.avatar) if message.author.avatar else None
            )
            user.last_seen_at = datetime.datetime.now(datetime.timezone.utc)
            await user_repo.update_user(user)
            
            await session.commit()
            
            # Track first response time
            if is_staff(message.author) and not ticket.first_response_at:
                ticket.first_response_at = datetime.datetime.now(datetime.timezone.utc)
                await ticket_repo.update_ticket(ticket)
                await session.commit()
                
                # Update claimer response time stats
                if ticket.claimed_by:
                    claimer = await user_repo.get_user(ticket.claimed_by)
                    if claimer:
                        response_seconds = int((ticket.first_response_at - ticket.created_at).total_seconds())
                        await user_repo.update_response_time(claimer, response_seconds)
                        await session.commit()
            
            # Handle auto-translation
            guild_config = await guild_repo.get_guild_config(message.guild.id)
            if guild_config and guild_config.enable_translation and message.content:
                try:
                    translation_service = get_translation_service()
                    
                    # Translate for ticket owner if they have auto-translate enabled
                    owner = await user_repo.get_user(ticket.owner_id)
                    if owner and owner.auto_translate and owner.language != "en":
                        if message.author.id != ticket.owner_id:  # Don't translate owner's own messages
                            translated = await translation_service.translate_text(
                                message.content,
                                owner.language
                            )
                            if translated:
                                # Send translation as a reply
                                translation_embed = discord.Embed(
                                    description=f"**Original ({message.author.display_name}):**\n{message.content}\n\n"
                                           f"**Translated ({owner.language}):**\n{translated}",
                                    color=0x5865F2,
                                )
                                await message.reply(embed=translation_embed)
                                logger.info(f"Auto-translated message for user {ticket.owner_id}")
                    
                    # Translate for staff if they have auto-translate enabled
                    if is_staff(message.author) and user.auto_translate and user.language != "en":
                        if message.author.id != ticket.owner_id:  # Only translate user messages to staff
                            translated = await translation_service.translate_text(
                                message.content,
                                user.language
                            )
                            if translated:
                                translation_embed = discord.Embed(
                                    description=f"**Original ({message.author.display_name}):**\n{message.content}\n\n"
                                           f"**Translated ({user.language}):**\n{translated}",
                                    color=0x5865F2,
                                )
                                await message.reply(embed=translation_embed)
                                logger.info(f"Auto-translated message for staff {message.author.id}")
                
                except Exception as e:
                    logger.error(f"Error in auto-translation: {e}")
    
    @app_commands.command(name="panel", description="Post the support panel (admin only)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="Channel to post the panel in")
    async def panel_command(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Post the support panel in a channel."""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        # Clean up old panels
        cleaned = 0
        try:
            async for msg in channel.history(limit=50):
                if msg.author.id != self.bot.user.id or not msg.embeds:
                    continue
                title = (msg.embeds[0].title or "")
                if "Reyex Support" in title or "support ticket" in (msg.embeds[0].description or "").lower():
                    try:
                        await msg.delete()
                        cleaned += 1
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Error cleaning old panels: {e}")

        # Post new panel with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await channel.send(embed=build_panel_embed(interaction.guild), view=TicketPanelView(interaction.guild.id))
                extra = f" (cleaned {cleaned} old panel(s))" if cleaned else ""
                await interaction.followup.send(f"✅ Panel posted in {channel.mention}{extra}.", ephemeral=True)
                return
            except discord.HTTPException as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to post panel after {max_retries} attempts: {e}")
                    await interaction.followup.send(
                        f"❌ Failed to post panel in {channel.mention}. The bot may lack permissions or Discord is experiencing issues.",
                        ephemeral=True
                    )
                else:
                    logger.warning(f"Panel post attempt {attempt + 1} failed, retrying...")
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Unexpected error posting panel: {e}")
                await interaction.followup.send(
                    f"❌ An error occurred while posting the panel: {str(e)}",
                    ephemeral=True
                )
                return
    
    @app_commands.command(name="close", description="Close this ticket")
    @app_commands.describe(reason="Reason for closing the ticket")
    async def close_command(self, interaction: discord.Interaction, reason: str = "No reason given"):
        """Close the current ticket."""
        await self.close_ticket(interaction, reason)
    
    @app_commands.command(name="claim", description="Claim this ticket (staff only)")
    async def claim_command(self, interaction: discord.Interaction):
        """Claim the current ticket."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can claim tickets.", ephemeral=True)
        
        await self.claim_ticket(interaction)
    
    @app_commands.command(name="unclaim", description="Unclaim this ticket (staff only)")
    async def unclaim_command(self, interaction: discord.Interaction):
        """Unclaim the current ticket."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can unclaim tickets.", ephemeral=True)
        
        await self.unclaim_ticket(interaction)
    
    @app_commands.command(name="add", description="Add a user to this ticket")
    @app_commands.describe(member="User to add to the ticket")
    async def add_command(self, interaction: discord.Interaction, member: discord.Member):
        """Add a user to the current ticket."""
        await self.add_user_to_ticket(interaction, member)
    
    @app_commands.command(name="remove", description="Remove a user from this ticket (staff only)")
    @app_commands.describe(member="User to remove from the ticket")
    async def remove_command(self, interaction: discord.Interaction, member: discord.Member):
        """Remove a user from the current ticket."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can remove users.", ephemeral=True)
        
        await self.remove_user_from_ticket(interaction, member)
    
    @app_commands.command(name="transcript", description="Get ticket transcript")
    async def transcript_command(self, interaction: discord.Interaction):
        """Get a transcript of the current ticket."""
        await self.get_transcript(interaction)
    
    @app_commands.command(name="priority", description="Set ticket priority (staff only)")
    @app_commands.describe(level="Priority level (Low, Medium, High, Urgent)")
    @app_commands.choices(level=[
        app_commands.Choice(name="Low", value="Low"),
        app_commands.Choice(name="Medium", value="Medium"),
        app_commands.Choice(name="High", value="High"),
        app_commands.Choice(name="Urgent", value="Urgent"),
    ])
    async def priority_command(self, interaction: discord.Interaction, level: str):
        """Set ticket priority."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can change priority.", ephemeral=True)
        
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel.id)
            
            if not ticket:
                return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
            
            # Update priority
            ticket.priority = level
            ticket.last_activity = datetime.datetime.now(datetime.timezone.utc)
            await ticket_repo.update_ticket(ticket)
            await session.commit()
            
            # Refresh embed
            await self._refresh_ticket_embed(interaction.channel, ticket)
            
            priority_emoji = {"Low": "🟢", "Medium": "⚪", "High": "🟡", "Urgent": "🔴"}.get(level, "")
            await interaction.response.send_message(
                f"{priority_emoji} Priority → **{level}**",
                ephemeral=True
            )
            
            logger.info(f"Ticket #{ticket.number} priority set to {level} by {interaction.user.id}")
    
    @app_commands.command(name="lock", description="Lock ticket read-only (staff only)")
    async def lock_command(self, interaction: discord.Interaction):
        """Lock ticket so user can only read."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can lock tickets.", ephemeral=True)
        
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel.id)
            
            if not ticket:
                return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
            
            ticket.locked = True
            await ticket_repo.update_ticket(ticket)
            await session.commit()
            
            # Update permissions
            owner = interaction.guild.get_member(ticket.owner_id)
            if owner:
                try:
                    await interaction.channel.set_permissions(
                        owner,
                        view_channel=True,
                        read_message_history=True,
                        send_messages=False
                    )
                except discord.Forbidden:
                    return await interaction.response.send_message(
                        "I lack permission to manage channel permissions.",
                        ephemeral=True
                    )
            
            await interaction.response.send_message("🔒 Locked (user read-only).", ephemeral=True)
            logger.info(f"Ticket #{ticket.number} locked by {interaction.user.id}")
    
    @app_commands.command(name="unlock", description="Unlock ticket (staff only)")
    async def unlock_command(self, interaction: discord.Interaction):
        """Unlock ticket so user can send messages again."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can unlock tickets.", ephemeral=True)
        
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel.id)
            
            if not ticket:
                return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
            
            ticket.locked = False
            await ticket_repo.update_ticket(ticket)
            await session.commit()
            
            # Update permissions
            owner = interaction.guild.get_member(ticket.owner_id)
            if owner:
                try:
                    await interaction.channel.set_permissions(
                        owner,
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True,
                        attach_files=True,
                        embed_links=True
                    )
                except discord.Forbidden:
                    return await interaction.response.send_message(
                        "I lack permission to manage channel permissions.",
                        ephemeral=True
                    )
            
            await interaction.response.send_message("🔓 Unlocked.", ephemeral=True)
            logger.info(f"Ticket #{ticket.number} unlocked by {interaction.user.id}")
    
    @app_commands.command(name="rename", description="Rename ticket (staff only)")
    @app_commands.describe(suffix="New name suffix")
    async def rename_command(self, interaction: discord.Interaction, suffix: str):
        """Rename ticket channel."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can rename tickets.", ephemeral=True)
        
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel.id)
            
            if not ticket:
                return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
            
            clean = re.sub(r"[^a-z0-9-]", "", suffix.strip().lower().replace(" ", "-")) or "ticket"
            new_name = f"{self.ticket_prefix}{ticket.number:04d}-{clean}"[:90]
            
            try:
                await interaction.channel.edit(name=new_name)
                ticket.channel_name = new_name
                await ticket_repo.update_ticket(ticket)
                await session.commit()
                await interaction.response.send_message(f"✏️ Renamed to `{new_name}`", ephemeral=True)
                logger.info(f"Ticket #{ticket.number} renamed to {new_name} by {interaction.user.id}")
            except discord.Forbidden:
                await interaction.response.send_message(
                    "I lack permission to rename channels.",
                    ephemeral=True
                )
    
    @app_commands.command(name="note", description="Post a staff note")
    @app_commands.describe(text="Note content")
    async def note_command(self, interaction: discord.Interaction, text: str):
        """Post a staff note to the ticket."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can post notes.", ephemeral=True)
        
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel.id)
            
            if not ticket:
                return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
        
        embed = discord.Embed(
            title="📝 Staff Note",
            description=text[:2000],
            color=0xFEE75C,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("Note posted.", ephemeral=True)
        logger.info(f"Staff note posted to ticket #{ticket.number} by {interaction.user.id}")
    
    @app_commands.command(name="stats", description="Support stats (staff only)")
    async def stats_command(self, interaction: discord.Interaction):
        """Show support statistics."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can view stats.", ephemeral=True)
        
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            from sqlalchemy import select, func
            from bot.models.ticket import Ticket, TicketStatus, TicketPriority
            
            ticket_repo = TicketRepository(session)
            
            # Get ticket counts
            total_result = await session.execute(select(func.count(Ticket.id)))
            total_tickets = total_result.scalar() or 0
            
            open_result = await session.execute(
                select(func.count(Ticket.id)).where(Ticket.status == TicketStatus.OPEN)
            )
            open_tickets = open_result.scalar() or 0
            
            # Get by type
            by_type = {}
            for ticket_type in ["general", "billing", "technical", "report"]:
                type_result = await session.execute(
                    select(func.count(Ticket.id)).where(Ticket.ticket_type == ticket_type)
                )
                by_type[ticket_type] = type_result.scalar() or 0
            
            # Get by priority
            by_priority = {}
            for priority in [TicketPriority.LOW, TicketPriority.MEDIUM, TicketPriority.HIGH, TicketPriority.URGENT]:
                prio_result = await session.execute(
                    select(func.count(Ticket.id)).where(Ticket.priority == priority)
                )
                by_priority[priority.value] = prio_result.scalar() or 0
            
            # Get unclaimed count
            unclaimed_result = await session.execute(
                select(func.count(Ticket.id)).where(
                    and_(Ticket.status == TicketStatus.OPEN, Ticket.claimed_by.is_(None))
                )
            )
            unclaimed = unclaimed_result.scalar() or 0
        
        embed = discord.Embed(
            title="📊 Reyex Support — Stats",
            color=self.brand_color,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Open tickets", value=f"`{open_tickets}`", inline=True)
        embed.add_field(name="Unclaimed", value=f"`{unclaimed}`", inline=True)
        embed.add_field(name="Total created", value=f"`{total_tickets}`", inline=True)
        embed.add_field(
            name="By type",
            value="\n".join(f"{k}: `{v}`" for k, v in by_type.items()) or "`none`",
            inline=True
        )
        embed.add_field(
            name="By priority",
            value="\n".join(f"{k}: `{v}`" for k, v in by_priority.items()) or "`none`",
            inline=True
        )
        embed.set_footer(text="Reyex Support")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        subject: str,
        description: str,
        ticket_type: str = "general"
    ):
        """Create a new ticket."""
        async with get_session() as session:
            from sqlalchemy import select, func
            from bot.database.repositories.guild_repository import GuildRepository
            
            guild_repo = GuildRepository(session)
            guild_config = await guild_repo.get_or_create_guild_config(interaction.guild.id, interaction.guild.name)
            
            # Check ticket limit
            result = await session.execute(
                select(func.count(Ticket.id))
                .where(
                    Ticket.owner_id == interaction.user.id,
                    Ticket.status == TicketStatus.OPEN,
                    Ticket.guild_id == interaction.guild.id
                )
            )
            open_count = result.scalar() or 0
            
            max_open = guild_config.max_open_tickets_per_user if guild_config else self.max_open_tickets
            if open_count >= max_open:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"You already have {max_open} open ticket(s). Close one first.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"You already have {max_open} open ticket(s). Close one first.",
                        ephemeral=True
                    )
                return
            
            # Defer if not already done
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=True)
            
            # Get ticket number
            result = await session.execute(select(func.max(Ticket.number)))
            max_number = result.scalar() or 0
            number = max_number + 1
            
            # Create channel
            safe_type = re.sub(r"[^a-z0-9]+", "", ticket_type.lower()) or "general"
            ticket_prefix = guild_config.ticket_prefix if guild_config else self.ticket_prefix
            name = f"{ticket_prefix}{number:04d}-{safe_type}"[:90]
            
            # Get category from guild config
            category = None
            if guild_config.ticket_category_id:
                category = interaction.guild.get_channel(guild_config.ticket_category_id)
            
            # Check ticket limit from guild config
            max_open = guild_config.max_open_tickets_per_user if guild_config else self.max_open_tickets
            if open_count >= max_open:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"You already have {max_open} open ticket(s). Close one first.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"You already have {max_open} open ticket(s). Close one first.",
                        ephemeral=True
                    )
                return
            
            try:
                overwrites = self._get_ticket_overwrites(interaction.guild, interaction.user)
                channel = await interaction.guild.create_text_channel(
                    name=name,
                    category=category,
                    overwrites=overwrites,
                    topic=f"[{ticket_type}|Medium] #{number} {subject} | Owner:{interaction.user.id}",
                    reason=f"Reyex ticket #{number} ({ticket_type}) for {interaction.user}",
                )
            except discord.Forbidden:
                return await interaction.followup.send(
                    "I lack **Manage Channels** permission.",
                    ephemeral=True
                )
            
            # Create ticket in database
            now = datetime.datetime.now(datetime.timezone.utc)
            ticket = Ticket(
                number=number,
                guild_id=interaction.guild.id,
                channel_id=channel.id,
                owner_id=interaction.user.id,
                subject=subject,
                description=description,
                ticket_type=ticket_type,
                status=TicketStatus.OPEN,
                priority=TicketPriority.MEDIUM,
                last_activity=now,
                created_at=now,
                updated_at=now,
            )
            
            session.add(ticket)
            
            # Create/update user
            user = await session.get(User, interaction.user.id)
            if user:
                user.increment_tickets_created()
                user.last_seen_at = now
            else:
                user = User(
                    id=interaction.user.id,
                    username=interaction.user.name,
                    discriminator=interaction.user.discriminator,
                    global_name=interaction.user.global_name,
                    tickets_created=1,
                    last_seen_at=now,
                    created_at=now,
                    updated_at=now,
                )
                session.add(user)
            
            await session.commit()
            await session.refresh(ticket)
            
            # Create SLA events for the ticket
            if guild_config and guild_config.enable_automation:
                try:
                    from bot.services.sla_service import get_sla_service
                    sla_service = get_sla_service()
                    await sla_service.create_sla_events_for_ticket(ticket)
                    await session.commit()
                except Exception as e:
                    logger.error(f"Failed to create SLA events: {e}")
            
            # Send welcome message
            from bot.cogs.tickets import TicketControlView
            embed, card_file = build_welcome_embed(
                number=number,
                ticket_type={"id": ticket_type, "label": ticket_type.title(), "emoji": "🎫"},
                subject=subject,
                description=description,
                owner=interaction.user,
                priority="Medium",
                info={"auto_close": False}
            )
            
            # Get support role to ping from guild config
            support_role_id = guild_config.support_role_id if guild_config else settings.support_role_id
            ping = f"<@&{support_role_id}>" if support_role_id else ""
            
            await channel.send(
                content=f"{interaction.user.mention} {ping}".strip(),
                embed=embed,
                file=card_file,
                view=TicketControlView("Medium")
            )
            
            await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)
            logger.info(f"Ticket #{number} created by {interaction.user.id} in guild {interaction.guild.id}")
    
    def _get_ticket_overwrites(self, guild: discord.Guild, member: discord.Member) -> dict:
        """Get permission overwrites for a ticket channel."""
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True,
                manage_messages=True,
            ),
        }
        
        # Add support role if configured
        support_role_id = settings.support_role_id
        if support_role_id:
            role = guild.get_role(int(support_role_id))
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                )
        
        return overwrites
    
    async def close_ticket(self, interaction: discord.Interaction, reason: str = "No reason given"):
        """Close a ticket with transcript generation and channel deletion."""
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            from bot.database.repositories.user_repository import UserRepository
            from bot.database.repositories.guild_repository import GuildRepository
            
            ticket_repo = TicketRepository(session)
            user_repo = UserRepository(session)
            guild_repo = GuildRepository(session)
            
            # Get ticket from database
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel.id)
            if not ticket:
                return await interaction.response.send_message(
                    "This channel is not a ticket.",
                    ephemeral=True
                )
            
            await interaction.response.defer(ephemeral=True, thinking=True)
            
            # Generate transcript
            transcript_file = None
            try:
                transcript_file = await self._build_transcript_from_db(interaction.channel, ticket)
            except Exception as e:
                logger.error(f"Failed to generate transcript: {e}")
            
            # Log to transcript channel if configured
            guild_config = await guild_repo.get_guild_config(interaction.guild.id)
            transcript_channel_id = guild_config.transcript_channel_id if guild_config else None
            if transcript_channel_id and transcript_file:
                transcript_channel = interaction.guild.get_channel(transcript_channel_id)
                if transcript_channel:
                    try:
                        transcript_file.fp.seek(0)
                        embed = discord.Embed(
                            title=f"🔒 Closed: #{interaction.channel.name}",
                            color=0xED4245,
                            timestamp=datetime.datetime.now(datetime.timezone.utc),
                        )
                        embed.add_field(name="Subject", value=ticket.subject, inline=False)
                        embed.add_field(name="Type", value=ticket.ticket_type, inline=True)
                        embed.add_field(name="Priority", value=ticket.priority, inline=True)
                        embed.add_field(
                            name="Owner",
                            value=f"<@{ticket.owner_id}> (`{ticket.owner_id}`)",
                            inline=False,
                        )
                        embed.add_field(name="Closed by", value=interaction.user.mention, inline=True)
                        embed.add_field(name="Reason", value=reason[:1000], inline=False)
                        await transcript_channel.send(embed=embed, file=transcript_file)
                    except Exception as e:
                        logger.error(f"Failed to log transcript: {e}")
            
            # Update ticket in database
            await ticket_repo.close_ticket(ticket, resolved=True)
            
            # Update user stats
            owner = await user_repo.get_user(ticket.owner_id)
            if owner:
                await user_repo.increment_tickets_closed(owner)
            
            # Update claimer stats if claimed
            if ticket.claimed_by:
                claimer = await user_repo.get_user(ticket.claimed_by)
                if claimer:
                    await user_repo.increment_tickets_resolved(claimer)
            
            await session.commit()
            
            # Notify owner via DM
            owner_member = interaction.guild.get_member(ticket.owner_id)
            if owner_member:
                try:
                    await owner_member.send(
                        f"Your ticket **#{interaction.channel.name}** in **{interaction.guild.name}** was closed.\n"
                        f"**Reason:** {reason}"
                    )
                except Exception:
                    pass
            
            # Delete channel
            try:
                await interaction.channel.delete(reason=reason[:500])
            except Exception as e:
                logger.error(f"Failed to delete channel: {e}")
                await interaction.followup.send(
                    "Ticket closed but failed to delete channel.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("Ticket closed successfully.", ephemeral=True)
            
            logger.info(f"Ticket #{ticket.number} closed by {interaction.user.id}")
    
    async def claim_ticket(self, interaction: discord.Interaction):
        """Claim a ticket."""
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            from bot.database.repositories.user_repository import UserRepository
            
            ticket_repo = TicketRepository(session)
            user_repo = UserRepository(session)
            
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel.id)
            if not ticket:
                return await interaction.response.send_message(
                    "This channel is not a ticket.",
                    ephemeral=True
                )
            
            if ticket.claimed_by:
                return await interaction.response.send_message(
                    "This ticket is already claimed.",
                    ephemeral=True
                )
            
            # Claim ticket
            await ticket_repo.claim_ticket(ticket, interaction.user.id)
            
            # Update user stats
            claimer = await user_repo.get_or_create_user(
                interaction.user.id,
                interaction.user.name,
                str(interaction.user.discriminator),
                interaction.user.global_name,
                str(interaction.user.avatar) if interaction.user.avatar else None
            )
            await user_repo.set_staff_status(claimer, True)
            await user_repo.increment_tickets_claimed(claimer)
            
            await session.commit()
            
            # Refresh embed
            await self._refresh_ticket_embed(interaction.channel, ticket)
            
            await interaction.response.send_message(
                f"🙋 Ticket claimed by {interaction.user.mention}",
                ephemeral=True
            )
            
            logger.info(f"Ticket #{ticket.number} claimed by {interaction.user.id}")
    
    async def unclaim_ticket(self, interaction: discord.Interaction):
        """Unclaim a ticket."""
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel.id)
            if not ticket:
                return await interaction.response.send_message(
                    "This channel is not a ticket.",
                    ephemeral=True
                )
            
            if not ticket.claimed_by:
                return await interaction.response.send_message(
                    "This ticket is not claimed.",
                    ephemeral=True
                )
            
            if ticket.claimed_by != interaction.user.id and not is_staff(interaction.user):
                return await interaction.response.send_message(
                    "You can only unclaim your own tickets.",
                    ephemeral=True
                )
            
            # Unclaim ticket
            await ticket_repo.unclaim_ticket(ticket)
            await session.commit()
            
            # Refresh embed
            await self._refresh_ticket_embed(interaction.channel, ticket)
            
            await interaction.response.send_message(
                "Ticket unclaimed — back in the queue.",
                ephemeral=True
            )
            
            logger.info(f"Ticket #{ticket.number} unclaimed by {interaction.user.id}")
    
    async def add_user_to_ticket(self, interaction: discord.Interaction, member: discord.Member):
        """Add a user to a ticket."""
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel.id)
            if not ticket:
                return await interaction.response.send_message(
                    "This channel is not a ticket.",
                    ephemeral=True
                )
            
            # Check permissions
            if not is_staff(interaction.user) and interaction.user.id != ticket.owner_id:
                return await interaction.response.send_message(
                    "You can't add users to this ticket.",
                    ephemeral=True
                )
            
            # Set Discord permissions
            try:
                await interaction.channel.set_permissions(
                    member,
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "I lack permission to manage channel permissions.",
                    ephemeral=True
                )
            
            await interaction.response.send_message(
                f"➕ {member.mention} added to the ticket.",
                ephemeral=True
            )
            
            logger.info(f"User {member.id} added to ticket #{ticket.number} by {interaction.user.id}")
    
    async def remove_user_from_ticket(self, interaction: discord.Interaction, member: discord.Member):
        """Remove a user from a ticket."""
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel.id)
            if not ticket:
                return await interaction.response.send_message(
                    "This channel is not a ticket.",
                    ephemeral=True
                )
            
            if not is_staff(interaction.user):
                return await interaction.response.send_message(
                    "Only staff can remove users.",
                    ephemeral=True
                )
            
            if member.id == ticket.owner_id:
                return await interaction.response.send_message(
                    "Cannot remove the ticket owner.",
                    ephemeral=True
                )
            
            # Remove Discord permissions
            try:
                await interaction.channel.set_permissions(member, overwrite=None)
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "I lack permission to manage channel permissions.",
                    ephemeral=True
                )
            
            await interaction.response.send_message(
                f"➖ {member.mention} removed from the ticket.",
                ephemeral=True
            )
            
            logger.info(f"User {member.id} removed from ticket #{ticket.number} by {interaction.user.id}")
    
    async def get_transcript(self, interaction: discord.Interaction):
        """Get a transcript of the ticket."""
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel.id)
            
            if not ticket:
                return await interaction.response.send_message(
                    "This channel is not a ticket.",
                    ephemeral=True
                )
            
            await interaction.response.defer(ephemeral=True, thinking=True)
            
            try:
                transcript_file = await self._build_transcript_from_db(interaction.channel, ticket)
                await interaction.followup.send("📝 Transcript:", file=transcript_file, ephemeral=True)
            except Exception as e:
                logger.error(f"Failed to generate transcript: {e}")
                await interaction.followup.send(
                    "Failed to generate transcript.",
                    ephemeral=True
                )
    
    async def _build_transcript_from_db(self, channel: discord.TextChannel, ticket) -> discord.File:
        """Build transcript from database message history."""
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            messages = await ticket_repo.get_ticket_messages(ticket.id, limit=1000)
            
            header = (
                f"Reyex Support transcript — #{channel.name}\n"
                f"Subject: {ticket.subject} | Type: {ticket.ticket_type} | "
                f"Priority: {ticket.priority} | Owner: {ticket.owner_id}\n"
                f"Exported: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n"
                f"{'=' * 60}\n"
            )
            
            lines = [header]
            
            for msg in messages:
                ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                author_type = msg.author_type.upper()
                content = msg.content or "[embed]"
                
                if msg.attachments:
                    content += " [files: " + " ".join(msg.attachments) + "]"
                
                lines.append(f"[{ts}] {author_type} ({msg.author_id}): {content}")
            
            # Also get recent Discord messages not yet in DB
            try:
                async for discord_msg in channel.history(limit=50, oldest_first=False):
                    # Check if this message is already in our list
                    if any(str(discord_msg.id) in line for line in lines):
                        continue
                    
                    ts = discord_msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    author = f"{discord_msg.author} ({discord_msg.author.id})"
                    content = discord_msg.content or "[embed]"
                    
                    if discord_msg.attachments:
                        content += " [files: " + " ".join(a.url for a in discord_msg.attachments) + "]"
                    
                    if discord_msg.embeds and not discord_msg.content:
                        content += f" [embed: {discord_msg.embeds[0].title or 'untitled'}]"
                    
                    lines.insert(1, f"[{ts}] {author}: {content}")
            except Exception as e:
                logger.warning(f"Failed to fetch recent Discord messages: {e}")
            
            text = "\n".join(lines)
            buf = io.BytesIO(text.encode("utf-8"))
            return discord.File(buf, filename=f"transcript-{channel.name}.txt")
    
    async def _refresh_ticket_embed(self, channel: discord.TextChannel, ticket):
        """Refresh the ticket welcome embed to show current status."""
        try:
            # Find the welcome message
            async for msg in channel.history(limit=10):
                if msg.author.id == self.bot.user.id and msg.embeds:
                    embed = msg.embeds[0]
                    if embed.image:  # Check if it has an image (our card)
                        # Update the embed with new format
                        owner = channel.guild.get_member(ticket.owner_id)
                        if not owner:
                            return
                        
                        # Get ticket type info
                        from bot.utils.embeds import build_welcome_embed
                        ticket_type = {"id": ticket.ticket_type, "label": ticket.ticket_type.title(), "emoji": "🎫"}
                        
                        # Build info dict
                        info = {
                            "claimed_by": ticket.claimed_by,
                            "auto_close": ticket.auto_close,
                            "locked": ticket.locked,
                        }
                        
                        new_embed, card_file = build_welcome_embed(
                            ticket.number,
                            ticket_type,
                            ticket.subject,
                            ticket.description or "",
                            owner,
                            ticket.priority,
                            info
                        )
                        
                        # Edit message with new embed and file
                        await msg.edit(embed=new_embed, attachments=[card_file])
                        break
        except Exception as e:
            logger.error(f"Failed to refresh ticket embed: {e}")


class TicketPanelView(discord.ui.View):
    """View for the ticket panel with ticket type selection."""
    
    def __init__(self, guild_id: int = None):
        super().__init__(timeout=None)
        # Add ticket type select
        self.add_item(TicketTypeSelect(guild_id))


class TicketTypeSelect(discord.ui.Select):
    """Select menu for choosing ticket type."""
    
    def __init__(self, guild_id: int = None):
        self.guild_id = guild_id
        # Default ticket types if not configured
        default_types = [
            {"id": "general", "label": "General Support", "emoji": "💬", "description": "Questions, help & other requests"},
            {"id": "billing", "label": "Billing", "emoji": "💳", "description": "Payments, subscriptions & refunds"},
            {"id": "technical", "label": "Technical Issue", "emoji": "🔧", "description": "Bugs, errors & troubleshooting"},
            {"id": "report", "label": "Report a User", "emoji": "🚨", "description": "Report abuse, scams & rule breaks"},
        ]
        
        self.ticket_types = default_types
        self.disabled_types = []
        
        super().__init__(
            placeholder="Select a topic to open a ticket…",
            min_values=1,
            max_values=1,
            options=self._build_options(),
            custom_id="reyex:ticket_type_select"
        )
    
    async def _load_guild_config(self):
        """Load ticket types from guild config."""
        if not self.guild_id:
            return
        
        try:
            async with get_session() as session:
                from bot.database.repositories.guild_repository import GuildRepository
                guild_repo = GuildRepository(session)
                guild_config = await guild_repo.get_guild_config(self.guild_id)
                
                if guild_config and guild_config.ticket_types:
                    self.ticket_types = guild_config.ticket_types
                if guild_config and guild_config.disabled_ticket_types:
                    self.disabled_types = guild_config.disabled_ticket_types
        except Exception as e:
            logger.error(f"Failed to load guild config for ticket types: {e}")
    
    def _build_options(self):
        """Build select options from ticket types."""
        options = []
        for t in self.ticket_types:
            if t.get("id") in self.disabled_types:
                continue
            
            options.append(
                discord.SelectOption(
                    label=t.get("label", t.get("id", "Unknown")),
                    value=t.get("id", "unknown"),
                    description=t.get("description", "")[:100],
                    emoji=t.get("emoji", "🎫")
                )
            )
        return options
    
    async def callback(self, interaction: discord.Interaction):
        """Handle ticket type selection."""
        chosen = self.values[0]
        
        # Check if ticket type is disabled
        if chosen in self.disabled_types:
            ticket_type = next((t for t in self.ticket_types if t.get("id") == chosen), {})
            return await interaction.response.send_message(
                embed=discord.Embed(
                    title="⛔ Ticket Type Disabled",
                    description=(
                        f"The **{ticket_type.get('label', 'selected')}** ticket type has been disabled "
                        "by server management and is not available.\n\n"
                        "Please choose a different category, or contact staff directly if you need help."
                    ),
                    color=0xED4245,
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                ).set_footer(text="Reyex Support"),
                ephemeral=True
            )
        
        # Show modal for ticket details
        from bot.cogs.tickets import TicketCreateModal
        await interaction.response.send_modal(TicketCreateModal(chosen))


class TicketCreateModal(discord.ui.Modal):
    """Modal for creating a ticket with details."""
    
    def __init__(self, ticket_type: str = "general"):
        super().__init__(title=f"{ticket_type.title()} Ticket")
        self.ticket_type = ticket_type
        self.subject = discord.ui.TextInput(
            label="Subject",
            placeholder="Short summary…",
            max_length=100,
            required=True,
            default=ticket_type.title()
        )
        self.description = discord.ui.TextInput(
            label="Describe your issue",
            placeholder="Details, steps, screenshots…",
            style=discord.TextStyle.paragraph,
            max_length=1500,
            required=True
        )
        self.add_item(self.subject)
        self.add_item(self.description)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        # Get the cog instance
        cog = interaction.client.get_cog("TicketsCog")
        if cog:
            await cog.create_ticket(
                interaction,
                self.subject.value.strip(),
                self.description.value.strip(),
                self.ticket_type
            )


class TicketControlView(discord.ui.View):
    """View for ticket control buttons with optimized layout."""
    
    def __init__(self, priority: str = "Medium"):
        super().__init__(timeout=None)
        # Row 3: Priority select (its own row)
        self.add_item(PrioritySelect(priority))
    
    @discord.ui.button(label="Talk to a staff member", style=discord.ButtonStyle.success,
                       custom_id="reyex:talk_to_staff", emoji="🙋", row=0)
    async def talk_to_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle talk to staff button."""
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel_id)
            
            if not ticket:
                return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
            
            ticket.need_human = True
            ticket.last_activity = datetime.datetime.now(datetime.timezone.utc)
            await ticket_repo.update_ticket(ticket)
            await session.commit()
            
            support_role_id = settings.support_role_id
            ping = f"<@&{support_role_id}>" if support_role_id else "staff"
            
            embed = discord.Embed(
                title="!  Human support requested",
                description=(
                    f"Ticket #{ticket.number:04d}\n"
                    f"{DIVIDER}\n"
                    f"{ping} {interaction.user.mention} needs a staff member here.\n"
                    "Automated replies are **paused** until a teammate picks this up."
                ),
                color=0xFEE75C,
            )
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message(
                "Notified — a staff member will pick this up.",
                ephemeral=True
            )
            
            logger.info(f"Human support requested for ticket #{ticket.number} by {interaction.user.id}")
    
    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, custom_id="reyex:claim", row=1)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle claim button."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can claim.", ephemeral=True)
        
        cog = interaction.client.get_cog("TicketsCog")
        if cog:
            await cog.claim_ticket(interaction)
    
    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="reyex:close", row=1)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle close button."""
        await interaction.response.send_modal(CloseReasonModal())
    
    @discord.ui.button(label="Auto-close", style=discord.ButtonStyle.secondary,
                       custom_id="reyex:auto_close", row=2)
    async def auto_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle auto-close toggle."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff.", ephemeral=True)
        
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel_id)
            
            if not ticket:
                return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
            
            ticket.auto_close = not ticket.auto_close
            ticket.last_activity = datetime.datetime.now(datetime.timezone.utc)
            await ticket_repo.update_ticket(ticket)
            await session.commit()
            
            # Refresh embed
            cog = interaction.client.get_cog("TicketsCog")
            if cog:
                await cog._refresh_ticket_embed(interaction.channel, ticket)
            
            state = "ON — closes after 24h of inactivity" if ticket.auto_close else "OFF for this ticket"
            await interaction.response.send_message(f"⏰ Auto-close: **{state}**")
            
            logger.info(f"Auto-close set to {ticket.auto_close} for ticket #{ticket.number} by {interaction.user.id}")
    
    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary,
                       custom_id="reyex:transcript", emoji="📝", row=2)
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle transcript button."""
        cog = interaction.client.get_cog("TicketsCog")
        if cog:
            await cog.get_transcript(interaction)


class PrioritySelect(discord.ui.Select):
    """Select menu for changing ticket priority."""
    
    def __init__(self, current: str = "Medium"):
        priorities = ["Low", "Medium", "High", "Urgent"]
        emoji_map = {"Low": "🟢", "Medium": "🟡", "High": "🟡", "Urgent": "🔴"}
        
        options = [
            discord.SelectOption(
                label=p,
                value=p,
                description=f"Set priority to {p}",
                emoji=emoji_map.get(p, "⚪"),
                default=(p == current)
            )
            for p in priorities
        ]
        super().__init__(
            placeholder=f"Priority: {current}",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="reyex:priority_select",
            row=3
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle priority change."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can change priority.", ephemeral=True)
        
        async with get_session() as session:
            from bot.database.repositories.ticket_repository import TicketRepository
            
            ticket_repo = TicketRepository(session)
            ticket = await ticket_repo.get_ticket_by_channel_id(interaction.channel_id)
            
            if not ticket:
                return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
            
            # Update priority
            ticket.priority = self.values[0]
            ticket.last_activity = datetime.datetime.now(datetime.timezone.utc)
            await ticket_repo.update_ticket(ticket)
            await session.commit()
            
            # Refresh embed
            cog = interaction.client.get_cog("TicketsCog")
            if cog:
                await cog._refresh_ticket_embed(interaction.channel, ticket)
            
            priority_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🟡", "Urgent": "🔴"}.get(self.values[0], "")
            await interaction.response.send_message(
                f"{priority_emoji} Priority → **{self.values[0]}**",
                ephemeral=True
            )
            
            logger.info(f"Ticket #{ticket.number} priority set to {self.values[0]} via UI")


class CloseReasonModal(discord.ui.Modal, title="Close Ticket"):
    """Modal for providing close reason."""
    reason = discord.ui.TextInput(
        label="Close reason",
        placeholder="e.g. resolved, duplicate…",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission."""
        cog = interaction.client.get_cog("TicketsCog")
        if cog:
            await cog.close_ticket(interaction, self.reason.value.strip() or "No reason given")
