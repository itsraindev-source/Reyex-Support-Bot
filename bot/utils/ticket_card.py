"""
Ticket card image generator with caching.
Generates branded ticket cards for display in Discord embeds.
"""

import hashlib
import io
from functools import lru_cache
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


# Cache directory for generated cards
CACHE_DIR = Path(__file__).parent.parent / ".cache" / "ticket_cards"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# Color scheme (Reyex dark red/black)
COLORS = {
    'bg': '#1a1a1a',
    'card_bg': '#2d2d2d',
    'primary': '#8b0000',  # Dark red
    'text_primary': '#ffffff',
    'text_secondary': '#b0b0b0',
    'priority_high': '#ff4444',
    'priority_medium': '#ffaa00',
    'priority_low': '#44ff44',
    'priority_urgent': '#ff0000',
    'status_open': '#4488ff',
    'status_claimed': '#ffaa00',
    'status_locked': '#ff4444',
    'status_closed': '#44ff44',
    'status_resolved': '#44ff44',
}


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Get a font with fallback to default."""
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SF-Pro-Text-Regular.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    
    for path in font_paths:
        try:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        except:
            continue
    
    # Fallback to default
    return ImageFont.load_default()


def _get_cache_key(
    ticket_number: int,
    subject: str,
    status: str,
    priority: str,
    owner_name: str,
    ticket_type: str,
) -> str:
    """Generate a cache key for the ticket card."""
    data = f"{ticket_number}:{subject}:{status}:{priority}:{owner_name}:{ticket_type}"
    return hashlib.md5(data.encode()).hexdigest()


def _load_cached_card(cache_key: str) -> Optional[Image.Image]:
    """Load a cached card image if it exists."""
    cache_path = CACHE_DIR / f"{cache_key}.png"
    if cache_path.exists():
        try:
            return Image.open(cache_path)
        except:
            return None
    return None


def _save_cached_card(cache_key: str, image: Image.Image) -> None:
    """Save a card image to cache."""
    cache_path = CACHE_DIR / f"{cache_key}.png"
    try:
        image.save(cache_path, "PNG")
    except:
        pass


def create_ticket_card(
    ticket_number: int,
    subject: str,
    status: str,
    priority: str,
    owner_name: str,
    ticket_type: str = "General Support",
    use_cache: bool = True,
) -> Image.Image:
    """Generate a branded ticket card image.
    
    Args:
        ticket_number: The ticket number
        subject: The ticket subject/title
        status: Ticket status (open, claimed, closed, resolved, locked)
        priority: Ticket priority (low, medium, high, urgent)
        owner_name: Name of the ticket owner
        ticket_type: Type of ticket (e.g., "Technical Issue", "Billing")
        use_cache: Whether to use cached images
    
    Returns:
        PIL Image object with the ticket card
    """
    # Check cache first
    if use_cache:
        cache_key = _get_cache_key(ticket_number, subject, status, priority, owner_name, ticket_type)
        cached = _load_cached_card(cache_key)
        if cached:
            return cached
    
    # Card dimensions
    width = 800
    height = 200
    
    # Create image with dark background
    img = Image.new('RGB', (width, height), color=COLORS['bg'])
    draw = ImageDraw.Draw(img)
    
    # Draw card background with rounded corners effect
    card_rect = [20, 20, width - 20, height - 20]
    draw.rectangle(card_rect, fill=COLORS['card_bg'])
    
    # Left accent bar (status color)
    status_color = COLORS.get(f'status_{status.lower()}', COLORS['status_open'])
    draw.rectangle([20, 20, 40, height - 20], fill=status_color)
    
    # Fonts
    font_large = _get_font(32, bold=True)
    font_medium = _get_font(24)
    font_small = _get_font(18)
    
    # Ticket number (top left)
    ticket_id = f"#{ticket_number:04d}"
    draw.text((55, 35), ticket_id, fill=COLORS['primary'], font=font_large)
    
    # Ticket type (below number)
    draw.text((55, 75), ticket_type, fill=COLORS['text_secondary'], font=font_small)
    
    # Subject (middle)
    subject_display = subject[:50] + ("..." if len(subject) > 50 else "")
    draw.text((55, 110), subject_display, fill=COLORS['text_primary'], font=font_medium)
    
    # Status (bottom left)
    status_emoji = {
        "open": "🎫",
        "claimed": "🔒",
        "locked": "🔒",
        "closed": "✓",
        "resolved": "✓",
    }.get(status.lower(), "🎫")
    draw.text((55, 150), f"{status_emoji} {status.title()}", fill=COLORS['text_secondary'], font=font_small)
    
    # Owner (bottom right)
    owner_text = f"👤 {owner_name}"
    text_width = draw.textlength(owner_text, font=font_small)
    draw.text((width - 40 - text_width, 150), owner_text, fill=COLORS['text_secondary'], font=font_small)
    
    # Priority indicator (top right)
    priority_color = COLORS.get(f'priority_{priority.lower()}', COLORS['priority_medium'])
    priority_text = f"● {priority.upper()}"
    priority_width = draw.textlength(priority_text, font=font_small)
    draw.text((width - 40 - priority_width, 35), priority_text, fill=priority_color, font=font_small)
    
    # Reyex branding (bottom right watermark)
    draw.text((width - 100, height - 35), "REYEX", fill=COLORS['primary'], font=font_small)
    
    # Save to cache
    if use_cache:
        _save_cached_card(cache_key, img)
    
    return img


def create_ticket_card_bytes(
    ticket_number: int,
    subject: str,
    status: str,
    priority: str,
    owner_name: str,
    ticket_type: str = "General Support",
    use_cache: bool = True,
) -> bytes:
    """Generate a ticket card and return as bytes for Discord upload.
    
    Args:
        ticket_number: The ticket number
        subject: The ticket subject/title
        status: Ticket status (open, claimed, closed, resolved, locked)
        priority: Ticket priority (low, medium, high, urgent)
        owner_name: Name of the ticket owner
        ticket_type: Type of ticket (e.g., "Technical Issue", "Billing")
        use_cache: Whether to use cached images
    
    Returns:
        Bytes of the PNG image
    """
    img = create_ticket_card(
        ticket_number=ticket_number,
        subject=subject,
        status=status,
        priority=priority,
        owner_name=owner_name,
        ticket_type=ticket_type,
        use_cache=use_cache,
    )
    
    # Convert to bytes
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def clear_cache() -> None:
    """Clear all cached ticket cards."""
    for file in CACHE_DIR.glob("*.png"):
        try:
            file.unlink()
        except:
            pass
