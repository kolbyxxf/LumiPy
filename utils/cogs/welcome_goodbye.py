import discord
from discord import app_commands
from discord.ext import commands

from utils import storage
from utils.permissions import require_permission


class WelcomeGoodbye(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.welcome: dict = storage.load_welcome()
        self.goodbye: dict = storage.load_goodbye()

    @app_commands.command(name="setwelcome", description="Set the welcome channel")
    async def setwelcome(self, interaction: discord.Interaction, channel_id: str):
        if not await require_permission(interaction, "manage_guild"):
            return
        if not channel_id.isdigit():
            await interaction.response.send_message(
                "The channel ID must be a number.", ephemeral=True
            )
            return
        channel = interaction.guild.get_channel(int(channel_id))
        if channel is None:
            await interaction.response.send_message(
                "I can't find that channel.", ephemeral=True
            )
            return
        # Fixed: store as dict so on_member_join can read config["channel_id"]
        self.welcome[str(interaction.guild.id)] = {"channel_id": channel.id}
        storage.save_welcome(self.welcome)
        await interaction.response.send_message(
            f"Welcome channel set to {channel.mention}.", ephemeral=True
        )

    @app_commands.command(name="setgoodbye", description="Set the goodbye channel")
    async def setgoodbye(self, interaction: discord.Interaction, channel_id: str):
        if not await require_permission(interaction, "manage_guild"):
            return
        if not channel_id.isdigit():
            await interaction.response.send_message(
                "The channel ID must be a number.", ephemeral=True
            )
            return
        channel = interaction.guild.get_channel(int(channel_id))
        if channel is None:
            await interaction.response.send_message(
                "I can't find that channel.", ephemeral=True
            )
            return
        self.goodbye[str(interaction.guild.id)] = {"channel_id": channel.id}
        storage.save_goodbye(self.goodbye)
        await interaction.response.send_message(
            f"Goodbye channel set to {channel.mention}.", ephemeral=True
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = self.welcome.get(str(member.guild.id))
        if config is None:
            return
        channel = member.guild.get_channel(int(config["channel_id"]))
        if channel is None:
            return
        embed = discord.Embed(
            title="Welcome!",
            description=f"Welcome {member.mention} to **{member.guild.name}**!",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count}")
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = self.goodbye.get(str(member.guild.id))
        if config is None:
            return
        channel = member.guild.get_channel(int(config["channel_id"]))
        if channel is None:
            return
        embed = discord.Embed(
            title="Goodbye!",
            description=f"**{member.display_name}** has left {member.guild.name}.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeGoodbye(bot))
