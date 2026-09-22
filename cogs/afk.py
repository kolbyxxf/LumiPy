import discord
from discord import app_commands
from discord.ext import commands
from utils import storage

MAX_REASON_LENGTH = 100
MAX_LINES_PER_REPLY = 10

class AFK(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.afk_users: dict[str, dict[str, str]] = {}

    async def cog_load(self):
        raw = await storage.load_afk()
        data: dict[str, dict[str, str]] = {}
        for guild_id, users in raw.items():
            if not isinstance(users, dict): continue
            cleaned = {str(uid): reason for uid, reason in users.items() if isinstance(reason, str)}
            if cleaned: data[str(guild_id)] = cleaned
        self.afk_users = data

    def _get_reason(self, guild_id: int, user_id: int) -> str | None:
        return self.afk_users.get(str(guild_id), {}).get(str(user_id))

    async def _set_afk(self, guild_id: int, user_id: int, reason: str) -> None:
        self.afk_users.setdefault(str(guild_id), {})[str(user_id)] = reason
        await storage.set_afk(str(guild_id), str(user_id), reason)

    async def _clear_afk(self, guild_id: int, user_id: int) -> bool:
        guild_key = str(guild_id)
        user_key = str(user_id)
        users = self.afk_users.get(guild_key)
        if not users or user_key not in users:
            return False
        del users[user_key]
        if not users:
            del self.afk_users[guild_key]
        await storage.clear_afk(guild_key, user_key)
        return True

    @staticmethod
    async def _send(channel: discord.abc.Messageable, content: str) -> None:
        try:
            await channel.send(content, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            pass

    @app_commands.command(name="afk", description="Set yourself as AFK in this server")
    @app_commands.describe(reason="Why you're AFK")
    @app_commands.guild_only()
    async def afk(self, interaction: discord.Interaction, reason: app_commands.Range[str, 1, MAX_REASON_LENGTH] = "AFK"):
        await self._set_afk(interaction.guild_id, interaction.user.id, reason)
        await interaction.response.send_message(
            f"{interaction.user.mention} is now AFK: {reason}",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None: return
        guild_id = message.guild.id
        if await self._clear_afk(guild_id, message.author.id):
            await self._send(message.channel, f"Welcome back {message.author.mention}, I removed your AFK.")
        
        lines: list[str] = []
        for user in message.mentions:
            reason = self._get_reason(guild_id, user.id)
            if reason is not None:
                lines.append(f"{user.display_name} is AFK: {reason}")
            if len(lines) >= MAX_LINES_PER_REPLY: break
        if lines:
            await self._send(message.channel, "\n".join(lines))

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._clear_afk(member.guild.id, member.id)

async def setup(bot: commands.Bot):
    await bot.add_cog(AFK(bot))