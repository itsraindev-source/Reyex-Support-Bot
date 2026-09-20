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
    auto = "ON" if info.get("auto_close") else "Off for this ticket"
    
    status_line = "`STATUS` 🔒 Claimed" if info.get("claimed_by") else "`STATUS` 🎫 Open"
    agent_line = f"`AGENT` <@{info.get('claimed_by')}>" if info.get("claimed_by") else "`AGENT` _Unclaimed_"
    
    priority_dot = {"Low": "🟢", "Medium": "⚪", "High": "🟡", "Urgent": "🔴"}.get(priority, "⚪")
    
    embed = discord.Embed(
        title=f"◆ Ticket #{number:04d}",
        description=(
            f"{subject} · Reyex Support\n"
            f"{DIVIDER}\n"
            f"{status_line}\n"
            f"`OPENED BY` {owner.mention}\n"
            f"{agent_line}\n"
            f"`PRIORITY` {priority_dot} {priority}\n"
            f"`AUTO-CLOSE` {auto}\n"
            f"{DIVIDER}\n"
            "Tell us what happened in your own words — paste the exact error text "
            "and drop **screenshots** if you have them. Support replies right here.\n\n"
            "Need a person instead? Hit **Talk to a staff member** and automated replies stop immediately."
        ),
        color=BRAND_COLOR,
    )
    
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
