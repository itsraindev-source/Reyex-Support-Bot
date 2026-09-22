"""
Embed builders for Discord messages.
"""

import datetime
from typing import Optional

import discord

from bot.config import get_settings

settings = get_settings()
BRAND_COLOR = settings.brand_color
DIVIDER = "─────────────────────────────"


def build_panel_embed(guild: Optional[discord.Guild] = None) -> discord.Embed:
    """Build the support panel embed."""
    max_open = settings.max_open_tickets_per_user
    limit_word = "1 open ticket per person" if max_open == 1 else f"{max_open} open tickets per person"
    
    description = (
        "Open a private ticket with the team\n"
        f"{DIVIDER}\n"
        "Pick a topic and we open a **private channel** for you and the support team.\n\n"
        "`RESPONSE` answers start immediately, staff join when needed\n"
        "`PRIVACY` only you and support can read the channel\n"
        f"`LIMIT` {limit_word}"
    )
    
    embed = discord.Embed(
        title="◆ Reyex Support",
        description=description,
        color=BRAND_COLOR,
    )
    
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    return embed


def build_welcome_embed(
    number: int,
    ticket_type: dict,
    subject: str,
    description: str,
    owner: discord.Member,
    priority: str = "Medium",
    info: Optional[dict] = None
) -> discord.Embed:
    """Build the welcome embed for a new ticket."""
    info = info or {}
    
    # Dynamic color based on priority and status
    is_claimed = info.get("claimed_by")
    priority_colors = {
        "Low": 0x57F287,      # Green
        "Medium": 0xFEE75C,    # Yellow
        "High": 0xED4245,     # Red
        "Urgent": 0xED4245,    # Red
    }
    status_colors = {
        "open": 0x5865F2,      # Blurple
        "claimed": 0xFEE75C,  # Yellow
        "locked": 0xED4245,   # Red
        "resolved": 0x57F287, # Green
    }
    
    if info.get("locked"):
        embed_color = status_colors["locked"]
    elif is_claimed:
        embed_color = status_colors["claimed"]
    else:
        embed_color = priority_colors.get(priority, status_colors["open"])
    
    # Ticket type emoji and icon
    type_emoji = ticket_type.get("emoji", "🎫")
    type_label = ticket_type.get("label", "Support")
    
    # Build embed
    embed = discord.Embed(
        title=subject,
        description=(
            f"Tell us what happened in your own words — paste the exact error text "
            "and drop **screenshots** if you have them. Support replies right here.\n\n"
            "Need a person instead? Hit **Talk to a staff member** and automated replies stop immediately."
        ),
        color=embed_color,
    )
    
    # Author line with ticket number and category
    embed.set_author(
        name=f"#{number:04d} · {type_emoji} {type_label}",
        icon_url=owner.display_avatar.url if owner.display_avatar else None
    )
    
    # Embed fields with clean formatting
    status_emoji = "🔒" if is_claimed else "🎫"
    status_text = "Claimed" if is_claimed else "Open"
    
    agent_name = f"<@{info.get('claimed_by')}>" if is_claimed else "_Unclaimed_"
    
    priority_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🟡", "Urgent": "🔴"}.get(priority, "⚪")
    
    auto_status = "ON" if info.get("auto_close") else "Off"
    
    embed.add_field(name="Status", value=f"{status_emoji} {status_text}", inline=True)
    embed.add_field(name="Agent", value=agent_name, inline=True)
    embed.add_field(name="Priority", value=f"{priority_emoji} {priority}", inline=True)
    embed.add_field(name="Auto-Close", value=auto_status, inline=True)
    embed.add_field(name="Opened By", value=owner.mention, inline=False)
    
    embed.set_footer(text="Reyex Support")
    
    return embed


def build_error_embed(title: str, message: str) -> discord.Embed:
    """Build an error embed."""
    return discord.Embed(
        title=f"❌ {title}",
        description=message,
        color=0xED4245,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    ).set_footer(text="Reyex Support")


def build_success_embed(title: str, message: str) -> discord.Embed:
    """Build a success embed."""
    return discord.Embed(
        title=f"✅ {title}",
        description=message,
        color=0x57F287,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    ).set_footer(text="Reyex Support")


def build_info_embed(title: str, message: str) -> discord.Embed:
    """Build an info embed."""
    return discord.Embed(
        title=f"ℹ️ {title}",
        description=message,
        color=0x5865F2,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    ).set_footer(text="Reyex Support")


def build_warning_embed(title: str, message: str) -> discord.Embed:
    """Build a warning embed."""
    return discord.Embed(
        title=f"⚠️ {title}",
        description=message,
        color=0xFEE75C,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    ).set_footer(text="Reyex Support")
