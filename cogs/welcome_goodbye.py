import discord
from discord import app_commands
from discord.ext import commands
from utils.storage import load_data, save_data

WELCOME_FILE = "welcome.json"
GOODBYE_FILE = "goodbye.json"

class WelcomeGoodbye(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setwelcome", description="Set the welcome message channel")
    @app_commands.default_permissions(manage_guild=True)
    async def set_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        data = load_data(WELCOME_FILE)
        data[str(interaction.guild.id)] = channel.id
        save_data(WELCOME_FILE, data)
        await interaction.response.send_message(f"Welcome channel set to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="setgoodbye", description="Set the goodbye message channel")
    @app_commands.default_permissions(manage_guild=True)
    async def set_goodbye(self, interaction: discord.Interaction, channel: discord.TextChannel):
        data = load_data(GOODBYE_FILE)
        data[str(interaction.guild.id)] = channel.id
        save_data(GOODBYE_FILE, data)
        await interaction.response.send_message(f"Goodbye channel set to {channel.mention}.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = load_data(WELCOME_FILE)
        channel_id = data.get(str(member.guild.id))
        if channel_id:
            channel = member.guild.get_channel(int(channel_id))
            if channel:
                await channel.send(f"Welcome to the server, {member.mention}! 🎉")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        data = load_data(GOODBYE_FILE)
        channel_id = data.get(str(member.guild.id))
        if channel_id:
            channel = member.guild.get_channel(int(channel_id))
            if channel:
                await channel.send(f"Goodbye {member.display_name}, we'll miss you! 👋")

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeGoodbye(bot))
