"""
Reyex Support — Discord support / ticket bot
Client ID: 1550588045533773884

Run:
  pip install -r requirements.txt
  python bot.py
Token is loaded from .env (DISCORD_TOKEN).
"""

import datetime
import io
import json
import os
import re
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
DATA_PATH = BASE_DIR / "data.json"

load_dotenv(BASE_DIR / ".env")
TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = json.load(f)

BRAND_COLOR = int(CONFIG.get("brand_color", 0x5865F2))
TICKET_TYPES = CONFIG.get("ticket_types", [
    {"id": "general", "label": "General Support", "emoji": "💬", "description": "Questions & help"},
])
PRIORITIES = CONFIG.get("priorities", ["Low", "Medium", "High", "Urgent"])
PRIORITY_COLORS = {"Low": 0x57F287, "Medium": 0x5865F2, "High": 0xFEE75C, "Urgent": 0xED4245}
PRIORITY_EMOJI = {"Low": "🟢", "Medium": "🔵", "High": "🟡", "Urgent": "🔴"}


def load_data():
    if not DATA_PATH.exists():
        return {"counter": 0, "tickets": {}}
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("counter", 0)
        data.setdefault("tickets", {})
        return data
    except (json.JSONDecodeError, OSError):
        return {"counter": 0, "tickets": {}}


def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_config():
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(CONFIG, f, indent=2)


def is_ticket_channel(channel, data=None) -> bool:
    if data is None:
        data = load_data()
    return str(getattr(channel, "id", channel)) in data.get("tickets", {})


def is_staff(member: discord.Member) -> bool:
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True
    role_ids = {r.id for r in getattr(member, "roles", [])}
    support_id = CONFIG.get("support_role_id")
    admin_id = CONFIG.get("admin_role_id")
    if support_id and int(support_id) in role_ids:
        return True
    if admin_id and int(admin_id) in role_ids:
        return True
    return False


def ticket_type_by_id(type_id: str) -> dict:
    for t in TICKET_TYPES:
        if t.get("id") == type_id:
            return t
    return {"id": "general", "label": "General Support", "emoji": "💬", "description": ""}


def is_ticket_type_disabled(type_id: str) -> bool:
    return type_id in CONFIG.get("disabled_ticket_types", [])


def build_type_disabled_embed(ticket_type: dict) -> discord.Embed:
    return discord.Embed(
        title="⛔ Ticket Type Disabled",
        description=(
            f"The **{ticket_type.get('label', 'selected')}** ticket type has been disabled "
            "by server management and is not available.\n\n"
            "Please choose a different category, or contact staff directly if you need help."
        ),
        color=0xED4245,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    ).set_footer(text="Reyex Support")


def open_ticket_count(data, user_id: int) -> int:
    return sum(1 for t in data["tickets"].values() if t.get("owner_id") == user_id)


# ---------- Embed builders ----------

DIVIDER = "─────────────────────────────"


def build_panel_embed(guild: Optional[discord.Guild] = None) -> discord.Embed:
    max_open = int(CONFIG.get("max_open_tickets_per_user", 3))
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


def ticket_status_line(info: dict) -> str:
    if info.get("claimed_by"):
        return f"`STATUS` 🔒 Claimed"
    return "`STATUS` 🎫 Open"


def ticket_agent_line(info: dict) -> str:
    agent = info.get("claimed_by")
    if agent:
        return f"`AGENT` <@{agent}>"
    return "`AGENT` _Unclaimed_"


def ticket_priority_dot(priority: str) -> str:
    return {"Low": "🟢", "Medium": "⚪", "High": "🟡", "Urgent": "🔴"}.get(priority, "⚪")


def build_welcome_embed(number: int, ticket_type: dict, subject: str, description: str,
                        owner: discord.Member, priority: str = "Medium",
                        info: Optional[dict] = None) -> discord.Embed:
    info = info or {}
    auto = "ON" if info.get("auto_close") else "Off for this ticket"
    embed = discord.Embed(
        title=f"◆ Ticket #{number:04d}",
        description=(
            f"{subject} · Reyex Support\n"
            f"{DIVIDER}\n"
            f"{ticket_status_line(info)}\n"
            f"`OPENED BY` {owner.mention}\n"
            f"{ticket_agent_line(info)}\n"
            f"`PRIORITY` {ticket_priority_dot(priority)} {priority}\n"
            f"`AUTO-CLOSE` {auto}\n"
            f"{DIVIDER}\n"
            "Tell us what happened in your own words — paste the exact error text "
            "and drop **screenshots** if you have them. Support replies right here.\n\n"
            "Need a person instead? Hit **Talk to a staff member** and automated replies stop immediately."
        ),
        color=BRAND_COLOR,
    )
    return embed


async def refresh_ticket_embed(channel: discord.TextChannel):
    """Re-render the ticket header embed so status/agent/priority stay current."""
    data = load_data()
    info = data["tickets"].get(str(channel.id))
    if not info:
        return
    msg_id = info.get("welcome_msg_id")
    if not msg_id:
        return
    try:
        msg = await channel.fetch_message(int(msg_id))
    except Exception:
        return
    owner = channel.guild.get_member(info["owner_id"])
    if not owner:
        return
    t = ticket_type_by_id(info.get("type", "general"))
    try:
        await msg.edit(embed=build_welcome_embed(
            info["number"], t, info.get("subject", "Support"),
            info.get("description", ""), owner,
            info.get("priority", "Medium"), info))
    except Exception:
        pass


# ---------- Ticket helpers ----------

def ticket_overwrites(guild: discord.Guild, member: discord.Member) -> dict:
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True,
            attach_files=True, embed_links=True,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True,
            read_message_history=True, manage_messages=True,
        ),
    }
    support_id = CONFIG.get("support_role_id")
    if support_id:
        role = guild.get_role(int(support_id))
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True,
                attach_files=True, embed_links=True,
            )
    return overwrites


async def create_ticket(interaction: discord.Interaction, subject: str, description: str,
                        ticket_type_id: str = "general"):
    guild = interaction.guild
    data = load_data()
    max_open = int(CONFIG.get("max_open_tickets_per_user", 3))
    if open_ticket_count(data, interaction.user.id) >= max_open:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"You already have {max_open} open ticket(s). Close one first.", ephemeral=True)
        else:
            await interaction.followup.send("Ticket limit reached.", ephemeral=True)
        return

    # defer only if we haven't responded (select/button flows call modal first, so not deferred yet)
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True, thinking=True)

    ticket_type = ticket_type_by_id(ticket_type_id)
    data["counter"] += 1
    number = data["counter"]
    prefix = CONFIG.get("ticket_prefix", "ticket-")
    safe_type = re.sub(r"[^a-z0-9]+", "", ticket_type_id.lower()) or "general"
    name = f"{prefix}{number:04d}-{safe_type}"[:90]

    category = None
    cat_id = CONFIG.get("ticket_category_id")
    if cat_id:
        category = guild.get_channel(int(cat_id))

    try:
        channel = await guild.create_text_channel(
            name=name,
            category=category,
            overwrites=ticket_overwrites(guild, interaction.user),
            topic=f"[{ticket_type.get('label')}|Medium] #{number} {subject} | Owner:{interaction.user.id}",
            reason=f"Reyex ticket #{number} ({ticket_type_id}) for {interaction.user}",
        )
    except discord.Forbidden:
        return await interaction.followup.send(
            "I lack **Manage Channels** permission.", ephemeral=True)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data["tickets"][str(channel.id)] = {
        "number": number,
        "guild_id": guild.id,
        "owner_id": interaction.user.id,
        "subject": subject,
        "description": description,
        "type": ticket_type_id,
        "priority": "Medium",
        "claimed_by": None,
        "locked": False,
        "auto_close": False,
        "need_human": False,
        "last_activity": now,
        "created_at": now,
    }
    save_data(data)

    support_id = CONFIG.get("support_role_id")
    ping = f"<@&{support_id}>" if support_id else ""
    info = data["tickets"][str(channel.id)]
    embed = build_welcome_embed(number, ticket_type, subject, description,
                                interaction.user, "Medium", info)
    header = await channel.send(
        content=f"{interaction.user.mention} {ping}".strip(),
        embed=embed, view=TicketControlView("Medium"))
    info["welcome_msg_id"] = header.id
    save_data(data)
    await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)


async def build_transcript(channel: discord.TextChannel):
    data = load_data()
    info = data["tickets"].get(str(channel.id), {})
    header = (
        f"Reyex Support transcript — #{channel.name}\n"
        f"Subject: {info.get('subject', '?')} | Type: {info.get('type', '?')} | "
        f"Priority: {info.get('priority', '?')} | Owner: {info.get('owner_id', '?')}\n"
        f"Exported: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n{'=' * 60}\n"
    )
    lines = [header]
    async for msg in channel.history(limit=None, oldest_first=True):
        ts = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author = f"{msg.author} ({msg.author.id})"
        content = msg.content or "[embed]"
        if msg.attachments:
            content += " [files: " + " ".join(a.url for a in msg.attachments) + "]"
        if msg.embeds and not msg.content:
            content += f" [embed: {msg.embeds[0].title or 'untitled'}]"
        lines.append(f"[{ts}] {author}: {content}")
    text = "\n".join(lines)
    buf = io.BytesIO(text.encode("utf-8"))
    return discord.File(buf, filename=f"transcript-{channel.name}.txt"), text


async def close_ticket(interaction: discord.Interaction, reason: str = "No reason given"):
    channel = interaction.channel
    data = load_data()
    info = data["tickets"].pop(str(channel.id), None)
    save_data(data)
    owner = interaction.guild.get_member(info["owner_id"]) if info else None

    transcript_file = None
    try:
        transcript_file, _ = await build_transcript(channel)
    except Exception:
        pass

    log_id = CONFIG.get("transcript_channel_id")
    if log_id and transcript_file:
        log_channel = interaction.guild.get_channel(int(log_id))
        if log_channel:
            try:
                transcript_file.fp.seek(0)
            except Exception:
                pass
            t = ticket_type_by_id(info.get("type", "general")) if info else {"label": "?"}
            embed = discord.Embed(
                title=f"🔒 Closed: #{channel.name}",
                color=0xED4245,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.add_field(name="Subject", value=(info or {}).get("subject", "?"), inline=False)
            embed.add_field(name="Type", value=t.get("label", "?"), inline=True)
            embed.add_field(name="Priority", value=(info or {}).get("priority", "?"), inline=True)
            embed.add_field(
                name="Owner",
                value=f"<@{(info or {}).get('owner_id', '?')}> (`{(info or {}).get('owner_id', '?')}`)",
                inline=False,
            )
            embed.add_field(name="Closed by", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason[:1000], inline=False)
            try:
                await log_channel.send(embed=embed, file=transcript_file)
            except Exception:
                await log_channel.send(embed=embed)

    if not interaction.response.is_done():
        await interaction.response.send_message("Closing ticket…", ephemeral=True)
    else:
        try:
            await interaction.followup.send("Closing ticket…", ephemeral=True)
        except Exception:
            pass
    if owner:
        try:
            await owner.send(
                f"Your ticket **#{channel.name}** in **{interaction.guild.name}** was closed.\n**Reason:** {reason}")
        except Exception:
            pass
    await channel.delete(reason=reason[:500])


def parse_member_input(guild: discord.Guild, text: str) -> Optional[discord.Member]:
    m = re.search(r"(\d{15,25})", text or "")
    if not m:
        return None
    return guild.get_member(int(m.group(1)))


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ---------- Modals ----------

class TicketCreateModal(discord.ui.Modal):
    def __init__(self, ticket_type_id: str = "general"):
        t = ticket_type_by_id(ticket_type_id)
        super().__init__(title=f"{t.get('label', 'Support')} Ticket")
        self.ticket_type_id = ticket_type_id
        self.subject = discord.ui.TextInput(
            label="Subject", placeholder="Short summary…", max_length=100, required=True,
            default=t.get("label", ""))
        self.description = discord.ui.TextInput(
            label="Describe your issue", placeholder="Details, steps, screenshots…",
            style=discord.TextStyle.paragraph, max_length=1500, required=True)
        self.add_item(self.subject)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket(interaction, self.subject.value.strip(),
                            self.description.value.strip(), self.ticket_type_id)


class CloseReasonModal(discord.ui.Modal, title="Close Ticket"):
    reason = discord.ui.TextInput(label="Close reason", placeholder="e.g. resolved, duplicate…",
                                  style=discord.TextStyle.paragraph, max_length=500, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await close_ticket(interaction, reason=(self.reason.value.strip() or "No reason given"))


class RenameModal(discord.ui.Modal, title="Rename Ticket"):
    suffix = discord.ui.TextInput(label="New name suffix", placeholder="e.g. billing-urgent",
                                  max_length=40, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        info = data["tickets"].get(str(interaction.channel_id))
        if not info:
            return await interaction.response.send_message("Not a ticket.", ephemeral=True)
        clean = re.sub(r"[^a-z0-9-]", "", self.suffix.value.strip().lower().replace(" ", "-")) or "ticket"
        prefix = CONFIG.get("ticket_prefix", "ticket-")
        new_name = f"{prefix}{info['number']:04d}-{clean}"[:90]
        try:
            await interaction.channel.edit(name=new_name)
            await interaction.response.send_message(f"✏️ Renamed to `{new_name}`")
        except discord.Forbidden:
            await interaction.response.send_message("I lack permission to rename.", ephemeral=True)


class AddUserModal(discord.ui.Modal, title="Add User to Ticket"):
    user = discord.ui.TextInput(label="User", placeholder="@mention or user ID", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        member = parse_member_input(interaction.guild, self.user.value)
        if not member:
            return await interaction.response.send_message("User not found. Use @mention or ID.", ephemeral=True)
        await interaction.channel.set_permissions(
            member, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
        await interaction.response.send_message(f"➕ {member.mention} added to the ticket.")


class AssignModal(discord.ui.Modal, title="Assign Ticket"):
    user = discord.ui.TextInput(label="Assign to (staff)", placeholder="@mention or user ID", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        member = parse_member_input(interaction.guild, self.user.value)
        if not member:
            return await interaction.response.send_message("Staff member not found.", ephemeral=True)
        if not is_staff(member):
            return await interaction.response.send_message(f"{member.mention} is not staff.", ephemeral=True)
        data = load_data()
        info = data["tickets"].get(str(interaction.channel_id))
        if not info:
            return await interaction.response.send_message("Not a ticket.", ephemeral=True)
        info["claimed_by"] = member.id
        save_data(data)
        await interaction.response.send_message(f"📌 Ticket assigned to {member.mention} by {interaction.user.mention}")


# ---------- Views ----------

class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=t.get("label", tid), value=t.get("id", tid),
                description=(t.get("description") or "")[:100],
                emoji=t.get("emoji", "🎫"))
            for tid, t in [(t.get("id"), t) for t in TICKET_TYPES]
        ]
        super().__init__(placeholder="Select a topic to open a ticket…", min_values=1, max_values=1,
                         options=options, custom_id="reyex:ticket_type_select")

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        if is_ticket_type_disabled(chosen):
            return await interaction.response.send_message(
                embed=build_type_disabled_embed(ticket_type_by_id(chosen)), ephemeral=True)
        data = load_data()
        max_open = int(CONFIG.get("max_open_tickets_per_user", 3))
        if open_ticket_count(data, interaction.user.id) >= max_open:
            return await interaction.response.send_message(
                f"You already have {max_open} open ticket(s).", ephemeral=True)
        await interaction.response.send_modal(TicketCreateModal(self.values[0]))


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())


class PrioritySelect(discord.ui.Select):
    def __init__(self, current: str = "Medium"):
        options = [
            discord.SelectOption(label=p, value=p,
                                 description=f"Set priority to {p}",
                                 emoji={"Low": "🟢", "Medium": "⚪", "High": "🟡", "Urgent": "🔴"}.get(p, "⚪"),
                                 default=(p == current))
            for p in PRIORITIES
        ]
        super().__init__(placeholder=f"Priority: {current}", min_values=1, max_values=1,
                         options=options, custom_id="reyex:priority_select")

    async def callback(self, interaction: discord.Interaction):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can change priority.", ephemeral=True)
        data = load_data()
        info = data["tickets"].get(str(interaction.channel_id))
        if not info:
            return await interaction.response.send_message("Not a ticket.", ephemeral=True)
        info["priority"] = self.values[0]
        info["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_data(data)
        await refresh_ticket_embed(interaction.channel)
        await interaction.response.send_message(
            f"{ticket_priority_dot(info['priority'])} Priority → **{info['priority']}**")


class TicketControlView(discord.ui.View):
    """Axis-style controls: user handoff button + compact staff row + priority select."""
    def __init__(self, priority: str = "Medium"):
        super().__init__(timeout=None)
        self.add_item(PrioritySelect(priority))

    @discord.ui.button(label="Talk to a staff member", style=discord.ButtonStyle.success,
                       custom_id="reyex:talk_to_staff", emoji="🙋", row=0)
    async def talk_to_staff(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        info = data["tickets"].get(str(interaction.channel_id))
        if not info:
            return await interaction.response.send_message("Not a ticket.", ephemeral=True)
        info["need_human"] = True
        info["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_data(data)
        support_id = CONFIG.get("support_role_id")
        ping = f"<@&{support_id}>" if support_id else "staff"
        embed = discord.Embed(
            title="!  Human support requested",
            description=(
                f"Ticket #{info.get('number', '?'):04d}\n"
                f"{DIVIDER}\n"
                f"{ping} {interaction.user.mention} needs a staff member here.\n"
                "Automated replies are **paused** until a teammate picks this up."
            ),
            color=0xFEE75C,
        )
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("Notified — a staff member will pick this up.", ephemeral=True)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, custom_id="reyex:claim", row=1)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff can claim.", ephemeral=True)
        data = load_data()
        info = data["tickets"].get(str(interaction.channel_id))
        if not info:
            return await interaction.response.send_message("Not a ticket.", ephemeral=True)
        info["claimed_by"] = interaction.user.id
        info["need_human"] = False
        info["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_data(data)
        await refresh_ticket_embed(interaction.channel)
        await interaction.response.send_message(f"Ticket claimed by {interaction.user.mention}")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="reyex:close", row=1)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CloseReasonModal())

    @discord.ui.button(label="Auto-close", style=discord.ButtonStyle.primary,
                       custom_id="reyex:auto_close", row=1)
    async def auto_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            return await interaction.response.send_message("Only staff.", ephemeral=True)
        data = load_data()
        info = data["tickets"].get(str(interaction.channel_id))
        if not info:
            return await interaction.response.send_message("Not a ticket.", ephemeral=True)
        info["auto_close"] = not info.get("auto_close", False)
        info["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_data(data)
        await refresh_ticket_embed(interaction.channel)
        state = "ON — closes after 24h of inactivity" if info["auto_close"] else "OFF for this ticket"
        await interaction.response.send_message(f"⏰ Auto-close: **{state}**")

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.secondary,
                       custom_id="reyex:transcript", emoji="📝", row=1)
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        file, _ = await build_transcript(interaction.channel)
        await interaction.followup.send("📝 Transcript:", file=file, ephemeral=True)


# ---------- Slash commands ----------

@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="Channel to post the panel in", support_role="Role pinged on new tickets")
async def setup_panel_cmd(interaction: discord.Interaction, channel: discord.TextChannel, support_role: discord.Role):
    CONFIG["support_role_id"] = support_role.id
    save_config()
    await interaction.response.defer(ephemeral=True, thinking=True)
    # Clean up old panels from this bot so /panel never stacks duplicates
    cleaned = 0
    try:
        async for msg in channel.history(limit=50):
            if msg.author.id != bot.user.id or not msg.embeds:
                continue
            title = (msg.embeds[0].title or "")
            if "Reyex Support" in title or "support ticket" in (msg.embeds[0].description or "").lower():
                try:
                    await msg.delete()
                    cleaned += 1
                except Exception:
                    pass
    except Exception:
        pass
    await channel.send(embed=build_panel_embed(interaction.guild), view=TicketPanelView())
    extra = f" (cleaned {cleaned} old panel(s))" if cleaned else ""
    await interaction.followup.send(f"✅ Panel posted in {channel.mention}{extra}.", ephemeral=True)


async def _clearpanels_cmd(interaction: discord.Interaction, channel: discord.TextChannel):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Only staff.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    cleaned = 0
    async for msg in channel.history(limit=100):
        if msg.author.id != bot.user.id or not msg.embeds:
            continue
        title = (msg.embeds[0].title or "")
        if "Reyex Support" in title or "support ticket" in (msg.embeds[0].description or "").lower():
            try:
                await msg.delete()
                cleaned += 1
            except Exception:
                pass
    await interaction.followup.send(f"🧹 Deleted {cleaned} panel message(s) in {channel.mention}.", ephemeral=True)


@app_commands.default_permissions(manage_guild=True)
@app_commands.describe(support_role="Role that manages tickets",
                       category="Category for new tickets",
                       transcript_channel="Channel for close logs")
async def setup_cmd(interaction: discord.Interaction,
                    support_role: Optional[discord.Role] = None,
                    category: Optional[discord.CategoryChannel] = None,
                    transcript_channel: Optional[discord.TextChannel] = None):
    if support_role:
        CONFIG["support_role_id"] = support_role.id
    if category:
        CONFIG["ticket_category_id"] = category.id
    if transcript_channel:
        CONFIG["transcript_channel_id"] = transcript_channel.id
    save_config()
    await interaction.response.send_message(
        f"✅ Saved.\nSupport: {support_role.mention if support_role else '`unchanged`'}\n"
        f"Category: {category.name if category else '`unchanged`'}\n"
        f"Transcripts: {transcript_channel.mention if transcript_channel else '`unchanged`'}",
        ephemeral=True)


async def _close_cmd(interaction: discord.Interaction, reason: str = "No reason given"):
    if not is_ticket_channel(interaction.channel):
        return await interaction.response.send_message("Only inside a ticket.", ephemeral=True)
    await close_ticket(interaction, reason=reason)


async def _add_cmd(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    info = data["tickets"].get(str(interaction.channel_id))
    if not info:
        return await interaction.response.send_message("Only inside a ticket.", ephemeral=True)
    if not is_staff(interaction.user) and interaction.user.id != info["owner_id"]:
        return await interaction.response.send_message("You can't add users here.", ephemeral=True)
    await interaction.channel.set_permissions(
        member, view_channel=True, send_messages=True, read_message_history=True, attach_files=True)
    await interaction.response.send_message(f"➕ {member.mention} added.")


async def _remove_cmd(interaction: discord.Interaction, member: discord.Member):
    if not is_ticket_channel(interaction.channel):
        return await interaction.response.send_message("Only inside a ticket.", ephemeral=True)
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Only staff.", ephemeral=True)
    await interaction.channel.set_permissions(member, overwrite=None)
    await interaction.response.send_message(f"➖ {member.mention} removed.")


async def _claim_cmd(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Only staff.", ephemeral=True)
    data = load_data()
    info = data["tickets"].get(str(interaction.channel_id))
    if not info:
        return await interaction.response.send_message("Not a ticket.", ephemeral=True)
    info["claimed_by"] = interaction.user.id
    info["need_human"] = False
    info["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save_data(data)
    await refresh_ticket_embed(interaction.channel)
    await interaction.response.send_message(f"🙋 Claimed by {interaction.user.mention}")


async def _unclaim_cmd(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Only staff.", ephemeral=True)
    data = load_data()
    info = data["tickets"].get(str(interaction.channel_id))
    if not info:
        return await interaction.response.send_message("Not a ticket.", ephemeral=True)
    info["claimed_by"] = None
    info["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save_data(data)
    await refresh_ticket_embed(interaction.channel)
    await interaction.response.send_message("Ticket unclaimed — back in the queue.")


async def _assign_cmd(interaction: discord.Interaction, member: discord.Member):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Only staff.", ephemeral=True)
    if not is_staff(member):
        return await interaction.response.send_message("Assign target must be staff.", ephemeral=True)
    data = load_data()
    info = data["tickets"].get(str(interaction.channel_id))
    if not info:
        return await interaction.response.send_message("Not a ticket.", ephemeral=True)
    info["claimed_by"] = member.id
    info["need_human"] = False
    info["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save_data(data)
    await refresh_ticket_embed(interaction.channel)
    await interaction.response.send_message(f"📌 Assigned to {member.mention}.")


async def _priority_cmd(interaction: discord.Interaction, level: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Only staff.", ephemeral=True)
    data = load_data()
    info = data["tickets"].get(str(interaction.channel_id))
    if not info:
        return await interaction.response.send_message("Not a ticket.", ephemeral=True)
    if level not in PRIORITIES:
        return await interaction.response.send_message(f"Choose: {', '.join(PRIORITIES)}", ephemeral=True)
    info["priority"] = level
    info["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save_data(data)
    await refresh_ticket_embed(interaction.channel)
    await interaction.response.send_message(f"{PRIORITY_EMOJI.get(level, '')} Priority → **{level}**")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    data = load_data()
    info = data["tickets"].get(str(message.channel.id))
    if info:
        info["last_activity"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save_data(data)
    await bot.process_commands(message)


@tasks.loop(minutes=10)
async def auto_close_loop():
    await bot.wait_until_ready()
    data = load_data()
    now = datetime.datetime.now(datetime.timezone.utc)
    changed = False
    for channel_id, info in list(data["tickets"].items()):
        if not info.get("auto_close"):
            continue
        try:
            last = datetime.datetime.fromisoformat(info.get("last_activity", info.get("created_at")))
            if last.tzinfo is None:
                last = last.replace(tzinfo=datetime.timezone.utc)
        except Exception:
            continue
        if (now - last).total_seconds() < 24 * 3600:
            continue
        guild_id = info.get("guild_id")
        channel = None
        for guild in bot.guilds:
            if guild_id and guild.id != guild_id:
                continue
            channel = guild.get_channel(int(channel_id))
            if channel:
                break
        if not channel:
            continue
        try:
            async for msg in channel.history(limit=20):
                pass
            transcript_file, _ = await build_transcript(channel)
            log_id = CONFIG.get("transcript_channel_id")
            if log_id:
                log_channel = channel.guild.get_channel(int(log_id))
                if log_channel:
                    embed = discord.Embed(
                        title=f"⏰ Auto-closed: #{channel.name}",
                        description=f"Inactive for 24h.\nOwner: <@{info['owner_id']}>",
                        color=0xFEE75C,
                        timestamp=now,
                    )
                    try:
                        await log_channel.send(embed=embed, file=transcript_file)
                    except Exception:
                        await log_channel.send(embed=embed)
            data["tickets"].pop(str(channel_id), None)
            changed = True
            await channel.delete(reason="Auto-close: 24h inactivity")
        except Exception as e:
            print(f"auto-close failed for {channel_id}: {e}")
    if changed:
        save_data(data)


async def _lock_cmd(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Only staff.", ephemeral=True)
    data = load_data()
    info = data["tickets"].get(str(interaction.channel_id))
    if not info:
        return await interaction.response.send_message("Not a ticket.", ephemeral=True)
    info["locked"] = True
    save_data(data)
    owner = interaction.guild.get_member(info["owner_id"])
    if owner:
        await interaction.channel.set_permissions(
            owner, view_channel=True, read_message_history=True, send_messages=False)
    await interaction.response.send_message("🔒 Locked (user read-only).")


async def _unlock_cmd(interaction: discord.Interaction):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Only staff.", ephemeral=True)
    data = load_data()
    info = data["tickets"].get(str(interaction.channel_id))
    if not info:
        return await interaction.response.send_message("Not a ticket.", ephemeral=True)
    info["locked"] = False
    save_data(data)
    owner = interaction.guild.get_member(info["owner_id"])
    if owner:
        await interaction.channel.set_permissions(
            owner, view_channel=True, send_messages=True, read_message_history=True)
    await interaction.response.send_message("🔓 Unlocked.")


async def _rename_cmd(interaction: discord.Interaction, suffix: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Only staff.", ephemeral=True)
    data = load_data()
    info = data["tickets"].get(str(interaction.channel_id))
    if not info:
        return await interaction.response.send_message("Not a ticket.", ephemeral=True)
    clean = re.sub(r"[^a-z0-9-]", "", suffix.strip().lower().replace(" ", "-")) or "ticket"
    new_name = f"{CONFIG.get('ticket_prefix', 'ticket-')}{info['number']:04d}-{clean}"[:90]
    await interaction.channel.edit(name=new_name)
    await interaction.response.send_message(f"✏️ Renamed to `{new_name}`")


async def _note_cmd(interaction: discord.Interaction, text: str):
    if not is_staff(interaction.user):
        return await interaction.response.send_message("Only staff.", ephemeral=True)
    if not is_ticket_channel(interaction.channel):
        return await interaction.response.send_message("Only inside a ticket.", ephemeral=True)
    embed = discord.Embed(title="📝 Staff Note", description=text[:2000],
                          color=0xFEE75C, timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("Note posted.", ephemeral=True)


async def _transcript_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    file, _ = await build_transcript(interaction.channel)
    await interaction.followup.send("📝 Transcript:", file=file, ephemeral=True)


async def _stats_cmd(interaction: discord.Interaction):
    data = load_data()
    tickets = list(data["tickets"].values())
    by_type, by_pri, unclaimed = {}, {}, 0
    for t in tickets:
        by_type[t.get("type", "?")] = by_type.get(t.get("type", "?"), 0) + 1
        by_pri[t.get("priority", "?")] = by_pri.get(t.get("priority", "?"), 0) + 1
        if not t.get("claimed_by"):
            unclaimed += 1
    embed = discord.Embed(title="📊 Reyex Support — Stats", color=BRAND_COLOR,
                          timestamp=datetime.datetime.now(datetime.timezone.utc))
    embed.add_field(name="Open tickets", value=f"`{len(tickets)}`", inline=True)
    embed.add_field(name="Unclaimed", value=f"`{unclaimed}`", inline=True)
    embed.add_field(name="Total created", value=f"`{data.get('counter', 0)}`", inline=True)
    embed.add_field(name="By type", value="\n".join(f"{k}: `{v}`" for k, v in by_type.items()) or "`none`", inline=True)
    embed.add_field(name="By priority", value="\n".join(f"{k}: `{v}`" for k, v in by_pri.items()) or "`none`", inline=True)
    embed.set_footer(text="Reyex Support")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.event
async def on_ready():
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    if not auto_close_loop.is_running():
        auto_close_loop.start()
    try:
        synced = await bot.tree.sync()
        print(f"Reyex Support online as {bot.user} — synced {len(synced)} global command(s).")
        # Instant per-guild sync so slash commands update immediately
        # (fixes Discord's "This command is outdated" cache error).
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                g_synced = await bot.tree.sync(guild=guild)
                print(f"  -> synced {len(g_synced)} command(s) to guild {guild.name} ({guild.id})")
            except Exception as e:
                print(f"  -> guild sync failed for {guild.id}: {e}")
    except Exception as e:
        print(f"Ready as {bot.user}, but command sync failed: {e}")


def _cmd(name: str, desc: str, callback, default_staff: bool = False):
    cmd = app_commands.Command(name=name, description=desc, callback=callback)
    if default_staff:
        cmd.default_permissions = discord.Permissions(manage_guild=True)
    return cmd


def register_commands():
    bot.tree.add_command(_cmd("panel", "Post the support panel (admin)", setup_panel_cmd))
    bot.tree.add_command(_cmd("setup", "Configure support role/category/transcripts", setup_cmd))
    bot.tree.add_command(_cmd("close", "Close this ticket", _close_cmd))
    bot.tree.add_command(_cmd("add", "Add a user to this ticket", _add_cmd))
    bot.tree.add_command(_cmd("remove", "Remove a user (staff)", _remove_cmd))
    bot.tree.add_command(_cmd("claim", "Claim this ticket (staff)", _claim_cmd))
    bot.tree.add_command(_cmd("unclaim", "Unclaim this ticket (staff)", _unclaim_cmd))
    bot.tree.add_command(_cmd("assign", "Assign ticket to staff", _assign_cmd))
    prio = _cmd("priority", "Set ticket priority (staff)", _priority_cmd)
    bot.tree.add_command(prio)
    bot.tree.add_command(_cmd("lock", "Lock ticket read-only (staff)", _lock_cmd))
    bot.tree.add_command(_cmd("unlock", "Unlock ticket (staff)", _unlock_cmd))
    bot.tree.add_command(_cmd("rename", "Rename ticket (staff)", _rename_cmd))
    bot.tree.add_command(_cmd("note", "Post a staff note", _note_cmd))
    bot.tree.add_command(_cmd("transcript", "Get ticket transcript", _transcript_cmd))
    bot.tree.add_command(_cmd("stats", "Support stats (staff)", _stats_cmd))
    bot.tree.add_command(_cmd("clearpanels", "Delete old bot panels in a channel (staff)", _clearpanels_cmd))


register_commands()


if __name__ == "__main__":
    if not TOKEN or TOKEN == "PUT_YOUR_TOKEN_HERE":
        raise SystemExit("Missing DISCORD_TOKEN. Put your bot token in .env")
    bot.run(TOKEN)
