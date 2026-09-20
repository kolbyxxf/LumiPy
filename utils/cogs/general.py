import random
import discord
from discord import app_commands
from discord.ext import commands

MAX_DICE = 20
MAX_SIDES = 1000

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


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hello", description="Says Hello!")
    async def say_hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Hi there {interaction.user}! What can I help you with?"
        )

    @app_commands.command(name="ping", description="Bots ping!")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong🏓! `{latency}ms`")

    @app_commands.command(name="roll", description="Roll dice")
    async def roll(
        self,
        interaction: discord.Interaction,
        sides: app_commands.Range[int, 1, MAX_SIDES] = 6,
        amount: app_commands.Range[int, 1, MAX_DICE] = 1,
    ):
        rolls = [random.randint(1, sides) for _ in range(amount)]
        await interaction.response.send_message(
            f"Rolled {amount}d{sides}: {rolls}\nTotal: `{sum(rolls)}`"
        )

    @app_commands.command(name="8ball", description="Ask the magic 8-ball")
    async def eightball(self, interaction: discord.Interaction, question: str):
        answer = random.choice(list(EIGHTBALL_ANSWERS))
        embed = discord.Embed(title="🎱 Magic 8-Ball", color=EIGHTBALL_ANSWERS[answer])
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=answer, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Show info about a member")
    async def userinfo(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ):
        member = member or interaction.user
        embed = discord.Embed(title=member.display_name, color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=member.name)
        embed.add_field(name="ID", value=f"`{member.id}`")
        embed.add_field(
            name="Account created",
            value=discord.utils.format_dt(member.created_at, "R"),
            inline=False,
        )
        if member.joined_at:
            embed.add_field(
                name="Joined server",
                value=discord.utils.format_dt(member.joined_at, "R"),
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Show info about this server")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return
        embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=f"<@{guild.owner_id}>")
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Roles", value=len(guild.roles))
        embed.add_field(name="Text channels", value=len(guild.text_channels))
        embed.add_field(name="Voice channels", value=len(guild.voice_channels))
        embed.add_field(
            name="Created",
            value=discord.utils.format_dt(guild.created_at, "R"),
            inline=False,
        )
        embed.set_footer(text=f"ID: {guild.id}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="See a user's avatar")
    async def avatar(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ):
        member = member or interaction.user
        embed = discord.Embed(title=member.display_name, color=member.color)
        embed.set_image(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(General(bot))
