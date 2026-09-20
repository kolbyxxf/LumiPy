import discord
from discord import app_commands
from discord.ext import commands

from utils import storage


class AFK(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.afk_users: dict[str, str] = storage.load_afk()

    @app_commands.command(name="afk", description="Set yourself as AFK")
    async def afk(self, interaction: discord.Interaction, reason: str = "AFK"):
        self.afk_users[str(interaction.user.id)] = reason
        storage.save_afk(self.afk_users)
        await interaction.response.send_message(
            f"{interaction.user.mention} is now AFK: {reason}"
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        user_id = str(message.author.id)
        if user_id in self.afk_users:
            self.afk_users.pop(user_id)
            storage.save_afk(self.afk_users)
            await message.channel.send(
                f"Welcome back {message.author.mention}, I removed your AFK."
            )

        for user in message.mentions:
            reason = self.afk_users.get(str(user.id))
            if reason:
                await message.channel.send(
                    f"{user.display_name} is AFK: {reason}"
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(AFK(bot))
