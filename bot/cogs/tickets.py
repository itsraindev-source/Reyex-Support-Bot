"""
Ticket management cog - core ticket functionality.
"""

import datetime
import io
import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import get_settings
from bot.database.connection import get_session
from bot.models.ticket import Ticket, TicketMessage, TicketStatus, TicketPriority
from bot.models.user import User
from bot.utils.embeds import build_panel_embed, build_welcome_embed
from bot.utils.logger import get_logger
from bot.utils.permissions import is_staff

logger = get_logger(__name__)

settings = get_settings()


class TicketsCog(commands.Cog):
    """Ticket management commands and events."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.brand_color = settings.brand_color
        self.ticket_prefix = settings.ticket_prefix
        self.max_open_tickets = settings.max_open_tickets_per_user
    
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
        
        # Post new panel
        from bot.cogs.tickets import TicketPanelView
        await channel.send(embed=build_panel_embed(interaction.guild), view=TicketPanelView())
        
        extra = f" (cleaned {cleaned} old panel(s))" if cleaned else ""
        await interaction.followup.send(f"✅ Panel posted in {channel.mention}{extra}.", ephemeral=True)
    
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
    
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        subject: str,
        description: str,
        ticket_type: str = "general"
    ):
        """Create a new ticket."""
        async with get_session() as session:
            # Check ticket limit
            from sqlalchemy import select, func
            
            result = await session.execute(
                select(func.count(Ticket.id))
                .where(
                    Ticket.owner_id == interaction.user.id,
                    Ticket.status == TicketStatus.OPEN,
                    Ticket.guild_id == interaction.guild.id
                )
            )
            open_count = result.scalar() or 0
            
            if open_count >= self.max_open_tickets:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        f"You already have {self.max_open_tickets} open ticket(s). Close one first.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"You already have {self.max_open_tickets} open ticket(s). Close one first.",
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
            name = f"{self.ticket_prefix}{number:04d}-{safe_type}"[:90]
            
            # Get category from config or guild
            category = None
            # In a real implementation, this would come from guild config
            # For now, we'll create the channel without a specific category
            
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
            
            # Send welcome message
            from bot.cogs.tickets import TicketControlView
            embed = build_welcome_embed(
                number=number,
                ticket_type={"id": ticket_type, "label": ticket_type.title(), "emoji": "🎫"},
                subject=subject,
                description=description,
                owner=interaction.user,
                priority="Medium",
                info={"auto_close": False}
            )
            
            # Get support role to ping
            support_role_id = settings.support_role_id
            ping = f"<@&{support_role_id}>" if support_role_id else ""
            
            await channel.send(
                content=f"{interaction.user.mention} {ping}".strip(),
                embed=embed,
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
        """Close a ticket."""
        # Implementation would be similar to original close_ticket function
        # This is a placeholder for the full implementation
        await interaction.response.send_message(
            f"Ticket close functionality - Reason: {reason}",
            ephemeral=True
        )
    
    async def claim_ticket(self, interaction: discord.Interaction):
        """Claim a ticket."""
        # Implementation would update the ticket with claimer
        await interaction.response.send_message(
            f"Ticket claimed by {interaction.user.mention}",
            ephemeral=True
        )
    
    async def unclaim_ticket(self, interaction: discord.Interaction):
        """Unclaim a ticket."""
        # Implementation would remove the claimer
        await interaction.response.send_message(
            "Ticket unclaimed",
            ephemeral=True
        )
    
    async def add_user_to_ticket(self, interaction: discord.Interaction, member: discord.Member):
        """Add a user to a ticket."""
        # Implementation would add permissions for the user
        await interaction.response.send_message(
            f"Added {member.mention} to the ticket",
            ephemeral=True
        )
    
    async def remove_user_from_ticket(self, interaction: discord.Interaction, member: discord.Member):
        """Remove a user from a ticket."""
        # Implementation would remove permissions for the user
        await interaction.response.send_message(
            f"Removed {member.mention} from the ticket",
            ephemeral=True
        )
    
    async def get_transcript(self, interaction: discord.Interaction):
        """Get a transcript of the ticket."""
        # Implementation would generate and send transcript
        await interaction.response.defer(ephemeral=True)
        
        # Generate transcript (placeholder)
        transcript = "Ticket transcript would be generated here"
        buf = io.BytesIO(transcript.encode("utf-8"))
        file = discord.File(buf, filename=f"transcript-{interaction.channel.name}.txt")
        
        await interaction.followup.send("📝 Transcript:", file=file, ephemeral=True)


class TicketPanelView(discord.ui.View):
    """View for the ticket panel with ticket type selection."""
    
    def __init__(self):
        super().__init__(timeout=None)
        # Add ticket type select
        self.add_item(TicketTypeSelect())


class TicketTypeSelect(discord.ui.Select):
    """Select menu for choosing ticket type."""
    
    def __init__(self):
        # This would be configured from settings in a real implementation
        options = [
            discord.SelectOption(
                label="General Support",
                value="general",
                description="Questions, help & other requests",
                emoji="💬"
            ),
            discord.SelectOption(
                label="Billing",
                value="billing",
                description="Payments, subscriptions & refunds",
                emoji="💳"
            ),
            discord.SelectOption(
                label="Technical Issue",
                value="technical",
                description="Bugs, errors & troubleshooting",
                emoji="🔧"
            ),
            discord.SelectOption(
                label="Report a User",
                value="report",
                description="Report abuse, scams & rule breaks",
                emoji="🚨"
            ),
        ]
        super().__init__(
            placeholder="Select a topic to open a ticket…",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="reyex:ticket_type_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle ticket type selection."""
        chosen = self.values[0]
        
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
    """View for ticket control buttons."""
    
    def __init__(self, priority: str = "Medium"):
        super().__init__(timeout=None)
        self.add_item(PrioritySelect(priority))
    
    @discord.ui.button(label="Talk to a staff member", style=discord.ButtonStyle.success,
                       custom_id="reyex:talk_to_staff", emoji="🙋", row=0)
    async def talk_to_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle talk to staff button."""
        await interaction.response.send_message(
            "A staff member will be with you shortly.",
            ephemeral=True
        )
    
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
        from bot.cogs.tickets import CloseReasonModal
        await interaction.response.send_modal(CloseReasonModal())
    
    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary,
                       custom_id="reyex:transcript", emoji="📝", row=1)
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle transcript button."""
        cog = interaction.client.get_cog("TicketsCog")
        if cog:
            await cog.get_transcript(interaction)


class PrioritySelect(discord.ui.Select):
    """Select menu for changing ticket priority."""
    
    def __init__(self, current: str = "Medium"):
        priorities = ["Low", "Medium", "High", "Urgent"]
        emoji_map = {"Low": "🟢", "Medium": "⚪", "High": "🟡", "Urgent": "🔴"}
        
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
            custom_id="reyex:priority_select"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle priority change."""
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can change priority.", ephemeral=True)
        
        # Update ticket priority in database
        # This would be implemented with the full database integration
        await interaction.response.send_message(
            f"Priority → **{self.values[0]}**",
            ephemeral=True
        )


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
