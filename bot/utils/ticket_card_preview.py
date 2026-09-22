"""
Preview script for ticket card image generation.
Run this to see what the ticket cards will look like.
"""

from PIL import Image, ImageDraw, ImageFont
import io


def create_ticket_card(
    ticket_number: int,
    subject: str,
    status: str,
    priority: str,
    owner_name: str,
    ticket_type: str = "General Support"
) -> Image.Image:
    """Generate a branded ticket card image."""
    
    # Card dimensions
    width = 800
    height = 200
    
    # Create image with dark background
    img = Image.new('RGB', (width, height), color='#1a1a1a')
    draw = ImageDraw.Draw(img)
    
    # Colors (Reyex dark red/black scheme)
    colors = {
        'bg': '#1a1a1a',
        'card_bg': '#2d2d2d',
        'primary': '#8b0000',  # Dark red
        'text_primary': '#ffffff',
        'text_secondary': '#b0b0b0',
        'priority_high': '#ff4444',
        'priority_medium': '#ffaa00',
        'priority_low': '#44ff44',
        'status_open': '#4488ff',
        'status_claimed': '#ffaa00',
        'status_closed': '#44ff44',
    }
    
    # Draw card background with rounded corners effect
    card_rect = [20, 20, width - 20, height - 20]
    draw.rectangle(card_rect, fill=colors['card_bg'])
    
    # Left accent bar (status color)
    status_color = colors.get(f'status_{status.lower()}', colors['status_open'])
    draw.rectangle([20, 20, 40, height - 20], fill=status_color)
    
    # Priority indicator (top right)
    priority_color = colors.get(f'priority_{priority.lower()}', colors['priority_medium'])
    priority_text = f"● {priority.upper()}"
    
    # Try to use system font, fallback to default
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Ticket number (top left)
    ticket_id = f"#{ticket_number:04d}"
    draw.text((55, 35), ticket_id, fill=colors['primary'], font=font_large)
    
    # Ticket type (below number)
    draw.text((55, 75), ticket_type, fill=colors['text_secondary'], font=font_small)
    
    # Subject (middle)
    draw.text((55, 110), subject[:50] + ("..." if len(subject) > 50 else ""),
              fill=colors['text_primary'], font=font_medium)
    
    # Status (bottom left)
    status_emoji = {"open": "🎫", "claimed": "🔒", "closed": "✓"}.get(status.lower(), "🎫")
    draw.text((55, 150), f"{status_emoji} {status.title()}", fill=colors['text_secondary'], font=font_small)
    
    # Owner (bottom right)
    owner_text = f"👤 {owner_name}"
    text_width = draw.textlength(owner_text, font=font_small)
    draw.text((width - 40 - text_width, 150), owner_text, fill=colors['text_secondary'], font=font_small)
    
    # Priority badge (top right)
    priority_width = draw.textlength(priority_text, font=font_small)
    draw.text((width - 40 - priority_width, 35), priority_text, fill=priority_color, font=font_small)
    
    # Reyex branding (bottom right watermark)
    draw.text((width - 100, height - 35), "REYEX", fill=colors['primary'], font=font_small)
    
    return img


if __name__ == "__main__":
    # Generate preview cards for different states
    print("Generating ticket card previews...")
    
    # Open ticket
    card1 = create_ticket_card(
        ticket_number=1234,
        subject="Login authentication failing",
        status="open",
        priority="high",
        owner_name="user123",
        ticket_type="Technical Issue"
    )
    card1.save("/tmp/ticket_open.png")
    print("✓ Saved: /tmp/ticket_open.png")
    
    # Claimed ticket
    card2 = create_ticket_card(
        ticket_number=1235,
        subject="Billing inquiry for subscription",
        status="claimed",
        priority="medium",
        owner_name="user456",
        ticket_type="Billing"
    )
    card2.save("/tmp/ticket_claimed.png")
    print("✓ Saved: /tmp/ticket_claimed.png")
    
    # Closed ticket
    card3 = create_ticket_card(
        ticket_number=1236,
        subject="Feature request for dashboard",
        status="closed",
        priority="low",
        owner_name="user789",
        ticket_type="General Support"
    )
    card3.save("/tmp/ticket_closed.png")
    print("✓ Saved: /tmp/ticket_closed.png")
    
    print("\nPreview images saved to /tmp/")
    print("Open them to see the ticket card design!")
