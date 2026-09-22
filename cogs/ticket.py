import os
import asyncio
from datetime import datetime, timezone, timedelta
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils import permissions, storage

ARCHIVE_DIR = "archives/tickets"
TICKET_LIFETIME = timedelta(days=7)
CHECK_INTERVAL = 6 * 60 * 60

class CloseView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=None)
        self.author_id = author_id

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket:close")
    async def close_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        tickets = await storage.load_tickets()
        ticket = tickets.get(str(interaction.channel.id))
        if not ticket: return await interaction.response.send_message("This isn't a registered ticket.", ephemeral=True)
        if ticket.get("status") == "closed": return await interaction.response.send_message("This ticket is already closed.", ephemeral=True)
        if not await _can_manage(interaction, ticket): return
        await _mark_closed(interaction, ticket)

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="ticket:create")
    async def create_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        await _open_ticket(interaction)

async def _can_manage(interaction: discord.Interaction, ticket: dict) -> bool:
    if interaction.user.id == ticket.get("owner_id"): return True
    return await permissions.require_permission(interaction, "manage_channels")

async def _mark_closed(interaction: discord.Interaction, ticket: dict) -> None:
    ticket["status"] = "closed"
    ticket["closed_at"] = datetime.now(timezone.utc).isoformat()
    await storage.set_ticket(str(interaction.channel.id), ticket)
    embed = discord.Embed(description="🔒 This ticket has been **closed**. It will be archived and deleted automatically after 7 days.", color=discord.Color.red())
    await interaction.response.edit_message(view=None)
    await interaction.channel.send(embed=embed)

async def _staff_mentions(guild: discord.Guild) -> str:
    staff = [m.mention for m in guild.members if not m.bot and m.guild_permissions.manage_channels][:10]
    return " ".join(staff) if staff else "@here"

async def _open_ticket(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    tickets = await storage.load_tickets()
    
    for info in tickets.values():
        if info.get("guild_id") == guild.id and info.get("owner_id") == interaction.user.id and info.get("status") != "closed":
            ch = guild.get_channel(info["channel_id"])
            return await interaction.response.send_message(f"You already have an open ticket: {ch.mention if ch else 'unknown'}", ephemeral=True)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
    }
    category = discord.utils.get(guild.categories, name="Tickets")
    if category is None:
        category = await guild.create_category("Tickets", overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=False)})
    
    safe_name = "".join(c for c in interaction.user.name.lower() if c.isalnum()) or "user"
    channel = await guild.create_text_channel(name=f"ticket-{safe_name}", category=category, overwrites=overwrites, topic=f"Ticket opened by {interaction.user} ({interaction.user.id})")
    
    ticket_info = {"guild_id": guild.id, "channel_id": channel.id, "owner_id": interaction.user.id, "owner_name": str(interaction.user), "status": "open", "created_at": datetime.now(timezone.utc).isoformat()}
    await storage.set_ticket(str(channel.id), ticket_info)
    
    embed = discord.Embed(title="🎫 Support Ticket", description=f"Hello {interaction.user.mention}, a staff member will be with you shortly.\nUse the button below or `/close` to end this ticket.", color=discord.Color.blurple())
    await channel.send(content=f"{await _staff_mentions(guild)} {interaction.user.mention}", embed=embed, view=CloseView(interaction.user.id))
    await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

async def _archive_transcript(channel: discord.TextChannel, ticket: dict) -> str | None:
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    path = os.path.join(ARCHIVE_DIR, f"{ticket['guild_id']}_{channel.id}.txt")
    lines = [f"Ticket Transcript — #{channel.name}", f"Owner: {ticket.get('owner_name')} ({ticket.get('owner_id')})", f"Opened: {ticket.get('created_at')}   Closed: {ticket.get('closed_at')}", "-" * 60]
    try:
        async for msg in channel.history(limit=None, oldest_first=True):
            lines.append(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M')}] {msg.author}: {msg.content}")
    except discord.Forbidden: pass
    with open(path, "w", encoding="utf-8") as f: f.write("\n".join(lines))
    return path

class Ticket(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cleanup_loop.start()

    async def cog_load(self) -> None:
        self.bot.add_view(CloseView(-1))
        self.bot.add_view(PanelView())

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def cleanup_loop(self) -> None:
        now = datetime.now(timezone.utc)
        tickets = await storage.load_tickets()
        for cid, ticket in list(tickets.items()):
            if ticket.get("status") != "closed" or not ticket.get("closed_at"): continue
            closed_at = datetime.fromisoformat(ticket["closed_at"])
            if now - closed_at < TICKET_LIFETIME: continue
            
            guild = self.bot.get_guild(ticket["guild_id"])
            channel = guild.get_channel(int(cid)) if guild else None
            path = await _archive_transcript(channel, ticket) if channel else None
            
            log_id = await storage.get_log_channel(str(ticket["guild_id"]))
            log_channel = guild.get_channel(log_id) if guild and log_id else None
            
            if log_channel:
                note = f"transcript saved to `{path}`" if path else "no transcript (channel gone)"
                await log_channel.send(f"🗑️ Ticket `{channel.name if channel else cid}` was closed on {closed_at.date()} and has been archived + deleted ({note}).")
            
            if channel:
                try: await channel.delete(reason="Ticket closed > 7 days — archived")
                except discord.HTTPException: pass
            await storage.remove_ticket(cid)

    @cleanup_loop.before_loop
    async def before_cleanup(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(name="ticket_panel", description="Post the ticket creation panel")
    async def panel_cmd(self, interaction: discord.Interaction):
        if not await permissions.require_permission(interaction, "manage_channels"): return
        embed = discord.Embed(title="Need help?", description="Click the button below to open a private ticket with our staff.", color=discord.Color.blurple())
        await interaction.channel.send(embed=embed, view=PanelView())
        await interaction.response.send_message("Ticket panel posted.", ephemeral=True)

    @app_commands.command(name="close", description="Close this ticket")
    async def close_cmd(self, interaction: discord.Interaction):
        tickets = await storage.load_tickets()
        ticket = tickets.get(str(interaction.channel.id))
        if not ticket: return await interaction.response.send_message("This channel is not a ticket.", ephemeral=True)
        if ticket.get("status") == "closed": return await interaction.response.send_message("Already closed.", ephemeral=True)
        if not await _can_manage(interaction, ticket): return
        await _mark_closed(interaction, ticket)

    def cog_unload(self) -> None:
        self.cleanup_loop.cancel()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Ticket(bot))