"""
Embed builders for Discord messages.
"""

import datetime
import io
from typing import Optional

import discord

from bot.config import get_settings
from bot.utils.ticket_card import create_ticket_card_bytes

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
) -> tuple[discord.Embed, discord.File]:
    """Build the welcome embed for a new ticket with branded card image.
    
    Returns:
        Tuple of (embed, file) where file is the ticket card image
    """
    info = info or {}
    
    # Determine status for the card
    is_claimed = info.get("claimed_by")
    if info.get("locked"):
        status = "locked"
    elif is_claimed:
        status = "claimed"
    else:
        status = "open"
    
    # Generate ticket card image
    type_label = ticket_type.get("label", "Support")
    card_bytes = create_ticket_card_bytes(
        ticket_number=number,
        subject=subject,
        status=status,
        priority=priority,
        owner_name=owner.display_name,
        ticket_type=type_label,
        use_cache=True,
    )
    
    # Create Discord file from bytes
    file = discord.File(
        fp=io.BytesIO(card_bytes),
        filename=f"ticket_{number}.png"
    )
    
    # Build minimal embed with card image
    embed = discord.Embed(
        description=(
            f"Tell us what happened in your own words — paste the exact error text "
            "and drop **screenshots** if you have them. Support replies right here.\n\n"
            "Need a person instead? Hit **Talk to a staff member** and automated replies stop immediately."
        ),
        color=0x2d2d2d,  # Dark gray to match card
    )
    
    embed.set_image(url=f"attachment://ticket_{number}.png")
    embed.set_footer(text="Reyex Support")
    
    return embed, file


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
