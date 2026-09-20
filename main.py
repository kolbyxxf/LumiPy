import os
import json
import random
import datetime

import discord
from discord import app_commands
from discord.ext import commands


# ══════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════

TOKEN = os.environ["DCTOKEN"]

GUILD_ID = discord.Object(id=1551112474487554148)

SETTINGS_FILE = "settings.json"
AFK_FILE = "afk.json"

MAX_DICE = 20
MAX_SIDES = 1000


# ══════════════════════════════════════════════
# JSON
# ══════════════════════════════════════════════

def load_settings() -> dict:
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_settings() -> None:
    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(settings, file, indent=4)


def load_afk() -> dict[str, str]:
    try:
        with open(AFK_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_afk() -> None:
    with open(AFK_FILE, "w", encoding="utf-8") as file:
        json.dump(afk_users, file, indent=4)


settings = load_settings()
afk_users: dict[str, str] = load_afk()


# ══════════════════════════════════════════════
# INTENTS
# ══════════════════════════════════════════════

intents = discord.Intents.default()
intents.message_content = True


# ══════════════════════════════════════════════
# BOT
# ══════════════════════════════════════════════

class Client(commands.Bot):

    async def setup_hook(self):
        try:
            synced = await self.tree.sync(guild=GUILD_ID)
            print(f"Synced {len(synced)} commands")

        except discord.HTTPException as error:
            print(f"Sync failed: {error}")

    async def on_ready(self):
        print(f"{self.user} is running fine!")

    async def on_message(self, message: discord.Message):

        if message.author.bot:
            return

        # ──────────────────────────────────────
        # REMOVE AFK WHEN USER TALKS
        # ──────────────────────────────────────

        user_id = str(message.author.id)

        if user_id in afk_users:
            afk_users.pop(user_id)
            save_afk()

            await message.channel.send(
                f"Welcome back {message.author.mention}, "
                "I removed your AFK."
            )

        # ──────────────────────────────────────
        # CHECK MENTIONED AFK USERS
        # ──────────────────────────────────────

        for user in message.mentions:

            mentioned_id = str(user.id)
            reason = afk_users.get(mentioned_id)

            if reason:
                await message.channel.send(
                    f"{user.display_name} is AFK: {reason}"
                )


client = Client(
    command_prefix="!",
    intents=intents
)


# ══════════════════════════════════════════════
# PERMISSION HELPERS
# ══════════════════════════════════════════════

async def require_permission(
    interaction: discord.Interaction,
    permission: str
) -> bool:

    if not getattr(interaction.user.guild_permissions, permission):
        await interaction.response.send_message(
            "You don't have permission.",
            ephemeral=True
        )
        return False

    return True


def can_moderate(
    interaction: discord.Interaction,
    member: discord.Member
) -> bool:

    if member == interaction.user:
        return False

    if interaction.guild is None:
        return False

    if interaction.user.id == interaction.guild.owner_id:
        return True

    return member.top_role < interaction.user.top_role


async def reject_target(
    interaction: discord.Interaction,
    member: discord.Member
) -> bool:

    if not can_moderate(interaction, member):
        await interaction.response.send_message(
            "You can't moderate that member.",
            ephemeral=True
        )
        return True

    return False


# ══════════════════════════════════════════════
# /HELLO
# ══════════════════════════════════════════════

@client.tree.command(
    name="hello",
    description="Says Hello!",
    guild=GUILD_ID
)
async def say_hello(interaction: discord.Interaction):

    await interaction.response.send_message(
        f"Hi there {interaction.user}! What can I help you with?"
    )


# ══════════════════════════════════════════════
# /PING
# ══════════════════════════════════════════════

@client.tree.command(
    name="ping",
    description="Bots ping!",
    guild=GUILD_ID
)
async def ping(interaction: discord.Interaction):

    latency = round(client.latency * 1000)

    await interaction.response.send_message(
        f"Pong🏓! `{latency}ms`"
    )


# ══════════════════════════════════════════════
# /ROLL
# ══════════════════════════════════════════════

@client.tree.command(
    name="roll",
    description="Roll dice",
    guild=GUILD_ID
)
async def roll(
    interaction: discord.Interaction,
    sides: app_commands.Range[int, 1, MAX_SIDES] = 6,
    amount: app_commands.Range[int, 1, MAX_DICE] = 1
):

    rolls = [
        random.randint(1, sides)
        for _ in range(amount)
    ]

    await interaction.response.send_message(
        f"Rolled {amount}d{sides}: {rolls}\n"
        f"Total: `{sum(rolls)}`"
    )


# ══════════════════════════════════════════════
# /8BALL
# ══════════════════════════════════════════════

EIGHTBALL_ANSWERS = {
    "Yes.": discord.Color.green(),
    "Definitely!": discord.Color.green(),
    "It looks good.": discord.Color.green(),

    "Maybe.": discord.Color.gold(),
    "Ask again later.": discord.Color.gold(),

    "No.": discord.Color.red(),
    "Not a chance.": discord.Color.red(),
    "I wouldn't count on it.": discord.Color.red(),
}


@client.tree.command(
    name="8ball",
    description="Ask the magic 8-ball",
    guild=GUILD_ID
)
async def eightball(
    interaction: discord.Interaction,
    question: str
):

    answer = random.choice(list(EIGHTBALL_ANSWERS))

    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        color=EIGHTBALL_ANSWERS[answer]
    )

    embed.add_field(
        name="Question",
        value=question,
        inline=False
    )

    embed.add_field(
        name="Answer",
        value=answer,
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


# ══════════════════════════════════════════════
# /USERINFO
# ══════════════════════════════════════════════

@client.tree.command(
    name="userinfo",
    description="Show info about a member",
    guild=GUILD_ID
)
async def userinfo(
    interaction: discord.Interaction,
    member: discord.Member | None = None
):

    member = member or interaction.user

    embed = discord.Embed(
        title=member.display_name,
        color=member.color
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="Username",
        value=member.name
    )

    embed.add_field(
        name="ID",
        value=f"`{member.id}`"
    )

    embed.add_field(
        name="Account created",
        value=discord.utils.format_dt(
            member.created_at,
            "R"
        ),
        inline=False
    )

    if member.joined_at:
        embed.add_field(
            name="Joined server",
            value=discord.utils.format_dt(
                member.joined_at,
                "R"
            ),
            inline=False
        )

    await interaction.response.send_message(
        embed=embed
    )


# ══════════════════════════════════════════════
# /SERVERINFO
# ══════════════════════════════════════════════

@client.tree.command(
    name="serverinfo",
    description="Show info about this server",
    guild=GUILD_ID
)
async def serverinfo(interaction: discord.Interaction):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=guild.name,
        color=discord.Color.blurple()
    )

    if guild.icon:
        embed.set_thumbnail(
            url=guild.icon.url
        )

    embed.add_field(
        name="Owner",
        value=f"<@{guild.owner_id}>"
    )

    embed.add_field(
        name="Members",
        value=guild.member_count
    )

    embed.add_field(
        name="Roles",
        value=len(guild.roles)
    )

    embed.add_field(
        name="Text channels",
        value=len(guild.text_channels)
    )

    embed.add_field(
        name="Voice channels",
        value=len(guild.voice_channels)
    )

    embed.add_field(
        name="Created",
        value=discord.utils.format_dt(
            guild.created_at,
            "R"
        ),
        inline=False
    )

    embed.set_footer(
        text=f"ID: {guild.id}"
    )

    await interaction.response.send_message(
        embed=embed
    )


# ══════════════════════════════════════════════
# /AVATAR
# ══════════════════════════════════════════════

@client.tree.command(
    name="avatar",
    description="See a user's avatar",
    guild=GUILD_ID
)
async def avatar(
    interaction: discord.Interaction,
    member: discord.Member | None = None
):

    member = member or interaction.user

    embed = discord.Embed(
        title=member.display_name,
        color=member.color
    )

    embed.set_image(
        url=member.display_avatar.url
    )

    await interaction.response.send_message(
        embed=embed
    )


# ══════════════════════════════════════════════
# /AFK
# ══════════════════════════════════════════════

@client.tree.command(
    name="afk",
    description="Set yourself as AFK",
    guild=GUILD_ID
)
async def afk(
    interaction: discord.Interaction,
    reason: str = "AFK"
):

    user_id = str(interaction.user.id)

    afk_users[user_id] = reason

    save_afk()

    await interaction.response.send_message(
        f"{interaction.user.mention} is now AFK: {reason}"
    )


# ══════════════════════════════════════════════
# /KICK
# ══════════════════════════════════════════════

@client.tree.command(
    name="kick",
    description="Kick a member",
    guild=GUILD_ID
)
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason"
):

    if not await require_permission(
        interaction,
        "kick_members"
    ):
        return

    if await reject_target(interaction, member):
        return

    try:
        await member.kick(reason=reason)

    except discord.Forbidden:
        await interaction.response.send_message(
            "I can't kick them, my role is too low.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"Kicked {member.display_name}. Reason: {reason}"
    )

    await mod_log(
        interaction.guild,
        "Member Kicked",
        interaction.user,
        member,
        reason
    )


# ══════════════════════════════════════════════
# /PURGE
# ══════════════════════════════════════════════

@client.tree.command(
    name="purge",
    description="Delete recent messages",
    guild=GUILD_ID
)
async def purge(
    interaction: discord.Interaction,
    amount: app_commands.Range[int, 1, 100]
):

    if not await require_permission(
        interaction,
        "manage_messages"
    ):
        return

    await interaction.response.defer(
        ephemeral=True
    )

    deleted = await interaction.channel.purge(
        limit=amount
    )

    await interaction.followup.send(
        f"Deleted {len(deleted)} messages.",
        ephemeral=True
    )


# ══════════════════════════════════════════════
# /TIMEOUT
# ══════════════════════════════════════════════

@client.tree.command(
    name="timeout",
    description="Mute a member for a while",
    guild=GUILD_ID
)
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: app_commands.Range[int, 1, 40320],
    reason: str = "No reason"
):

    if not await require_permission(
        interaction,
        "moderate_members"
    ):
        return

    if await reject_target(interaction, member):
        return

    try:
        await member.timeout(
            datetime.timedelta(minutes=minutes),
            reason=reason
        )

    except discord.Forbidden:
        await interaction.response.send_message(
            "I can't timeout them, my role is too low.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"Timed out {member.display_name} "
        f"for {minutes} minutes. Reason: {reason}"
    )

    await mod_log(
        interaction.guild,
        "Member Timed Out",
        interaction.user,
        member,
        reason
    )


# ══════════════════════════════════════════════
# /BAN
# ══════════════════════════════════════════════

@client.tree.command(
    name="ban",
    description="Ban a member",
    guild=GUILD_ID
)
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason"
):

    if not await require_permission(
        interaction,
        "ban_members"
    ):
        return

    if await reject_target(interaction, member):
        return

    try:
        await member.ban(reason=reason)

    except discord.Forbidden:
        await interaction.response.send_message(
            "I can't ban them, my role is too low.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"Banned {member.display_name}. Reason: {reason}"
    )

    await mod_log(
        interaction.guild,
        "Member Banned",
        interaction.user,
        member,
        reason
    )


# ══════════════════════════════════════════════
# /UNTIMEOUT
# ══════════════════════════════════════════════

@client.tree.command(
    name="untimeout",
    description="Remove a member's timeout",
    guild=GUILD_ID
)
async def untimeout(
    interaction: discord.Interaction,
    member: discord.Member
):

    if not await require_permission(
        interaction,
        "moderate_members"
    ):
        return

    if await reject_target(interaction, member):
        return

    try:
        await member.timeout(None)

    except discord.Forbidden:
        await interaction.response.send_message(
            "I can't do that, my role is too low.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"Removed the timeout for {member.display_name}."
    )

    await mod_log(
        interaction.guild,
        "Timeout Removed",
        interaction.user,
        member
    )


# ══════════════════════════════════════════════
# /UNBAN
# ══════════════════════════════════════════════

@client.tree.command(
    name="unban",
    description="Unban a user by their ID",
    guild=GUILD_ID
)
async def unban(
    interaction: discord.Interaction,
    user_id: str
):

    if not await require_permission(
        interaction,
        "ban_members"
    ):
        return

    if not user_id.isdigit():
        await interaction.response.send_message(
            "That isn't a valid user ID.",
            ephemeral=True
        )
        return

    try:
        await interaction.guild.unban(
            discord.Object(id=int(user_id))
        )

    except discord.NotFound:
        await interaction.response.send_message(
            "That user isn't banned.",
            ephemeral=True
        )
        return

    except discord.Forbidden:
        await interaction.response.send_message(
            "I can't unban, I'm missing the "
            "Ban Members permission.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"Unbanned <@{user_id}>."
    )

    await mod_log(
        interaction.guild,
        "Member Unbanned",
        interaction.user,
        f"<@{user_id}>"
    )


# ══════════════════════════════════════════════
# /SETLOG
# ══════════════════════════════════════════════

@client.tree.command(
    name="setlog",
    description="Set the mod log channel",
    guild=GUILD_ID
)
async def setlog(
    interaction: discord.Interaction,
    channel_id: str,
    server_id: str | None = None
):

    if server_id is None:

        if interaction.guild is None:
            await interaction.response.send_message(
                "Enter a server ID when using this in DMs.",
                ephemeral=True
            )
            return

        server_id = str(interaction.guild.id)

    if not server_id.isdigit() or not channel_id.isdigit():
        await interaction.response.send_message(
            "The IDs must be numbers only.",
            ephemeral=True
        )
        return

    guild = client.get_guild(
        int(server_id)
    )

    if guild is None:
        await interaction.response.send_message(
            "I'm not in that server.",
            ephemeral=True
        )
        return

    try:
        member = await guild.fetch_member(
            interaction.user.id
        )

    except discord.NotFound:
        await interaction.response.send_message(
            "You're not in that server.",
            ephemeral=True
        )
        return

    if not member.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "You need Manage Server permission "
            "in that server.",
            ephemeral=True
        )
        return

    channel = guild.get_channel(
        int(channel_id)
    )

    if channel is None:
        await interaction.response.send_message(
            "I can't find that channel in that server.",
            ephemeral=True
        )
        return

    settings[str(guild.id)] = channel.id

    save_settings()

    await interaction.response.send_message(
        f"Mod log for **{guild.name}** set to "
        f"{channel.mention}.",
        ephemeral=True
    )


# ══════════════════════════════════════════════
# MOD LOG
# ══════════════════════════════════════════════

async def mod_log(
    guild,
    action,
    moderator,
    target,
    reason="No reason"
):

    if guild is None:
        return

    channel_id = settings.get(
        str(guild.id)
    )

    if channel_id is None:
        return

    channel = guild.get_channel(
        int(channel_id)
    )

    if channel is None:
        return

    embed = discord.Embed(
        title=action,
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(
        name="Moderator",
        value=moderator.mention
    )

    embed.add_field(
        name="Target",
        value=str(target)
    )

    embed.add_field(
        name="Reason",
        value=reason,
        inline=False
    )

    try:
        await channel.send(
            embed=embed
        )

    except discord.Forbidden:
        pass


# ══════════════════════════════════════════════
# RUN
# ══════════════════════════════════════════════

client.run(TOKEN)