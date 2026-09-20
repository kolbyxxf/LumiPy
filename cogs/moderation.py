import datetime
import discord
from discord import app_commands
from discord.ext import commands

from utils import storage
from utils.permissions import require_permission, reject_target


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings: dict = storage.load_settings()

    async def mod_log(
        self,
        guild,
        action,
        moderator,
        target,
        reason="No reason",
    ):
        if guild is None:
            return
        channel_id = self.settings.get(str(guild.id))
        if channel_id is None:
            return
        channel = guild.get_channel(int(channel_id))
        if channel is None:
            return
        embed = discord.Embed(
            title=action,
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Moderator", value=moderator.mention)
        embed.add_field(name="Target", value=str(target))
        embed.add_field(name="Reason", value=reason, inline=False)
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @app_commands.command(name="kick", description="Kick a member")
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason",
    ):
        if not await require_permission(interaction, "kick_members"):
            return
        if await reject_target(interaction, member):
            return
        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I can't kick them, my role is too low.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"Kicked {member.display_name}. Reason: {reason}"
        )
        await self.mod_log(interaction.guild, "Member Kicked", interaction.user, member, reason)

    @app_commands.command(name="ban", description="Ban a member")
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason",
    ):
        if not await require_permission(interaction, "ban_members"):
            return
        if await reject_target(interaction, member):
            return
        try:
            await member.ban(reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I can't ban them, my role is too low.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"Banned {member.display_name}. Reason: {reason}"
        )
        await self.mod_log(interaction.guild, "Member Banned", interaction.user, member, reason)

    @app_commands.command(name="unban", description="Unban a user by their ID")
    async def unban(self, interaction: discord.Interaction, user_id: str):
        if not await require_permission(interaction, "ban_members"):
            return
        if not user_id.isdigit():
            await interaction.response.send_message(
                "That isn't a valid user ID.", ephemeral=True
            )
            return
        try:
            await interaction.guild.unban(discord.Object(id=int(user_id)))
        except discord.NotFound:
            await interaction.response.send_message(
                "That user isn't banned.", ephemeral=True
            )
            return
        except discord.Forbidden:
            await interaction.response.send_message(
                "I can't unban, I'm missing the Ban Members permission.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(f"Unbanned <@{user_id}>.")
        await self.mod_log(
            interaction.guild, "Member Unbanned", interaction.user, f"<@{user_id}>"
        )

    @app_commands.command(name="timeout", description="Mute a member for a while")
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str = "No reason",
    ):
        if not await require_permission(interaction, "moderate_members"):
            return
        if await reject_target(interaction, member):
            return
        try:
            await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I can't timeout them, my role is too low.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"Timed out {member.display_name} for {minutes} minutes. Reason: {reason}"
        )
        await self.mod_log(interaction.guild, "Member Timed Out", interaction.user, member, reason)

    @app_commands.command(name="untimeout", description="Remove a member's timeout")
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        if not await require_permission(interaction, "moderate_members"):
            return
        if await reject_target(interaction, member):
            return
        try:
            await member.timeout(None)
        except discord.Forbidden:
            await interaction.response.send_message(
                "I can't do that, my role is too low.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"Removed the timeout for {member.display_name}."
        )
        await self.mod_log(interaction.guild, "Timeout Removed", interaction.user, member)

    @app_commands.command(name="purge", description="Delete recent messages")
    async def purge(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100],
    ):
        if not await require_permission(interaction, "manage_messages"):
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            f"Deleted {len(deleted)} messages.", ephemeral=True
        )

    @app_commands.command(name="setlog", description="Set the mod log channel")
    async def setlog(
        self,
        interaction: discord.Interaction,
        channel_id: str,
        server_id: str | None = None,
    ):
        if server_id is None:
            if interaction.guild is None:
                await interaction.response.send_message(
                    "Enter a server ID when using this in DMs.", ephemeral=True
                )
                return
            server_id = str(interaction.guild.id)

        if not server_id.isdigit() or not channel_id.isdigit():
            await interaction.response.send_message(
                "The IDs must be numbers only.", ephemeral=True
            )
            return

        guild = self.bot.get_guild(int(server_id))
        if guild is None:
            await interaction.response.send_message(
                "I'm not in that server.", ephemeral=True
            )
            return

        try:
            member = await guild.fetch_member(interaction.user.id)
        except discord.NotFound:
            await interaction.response.send_message(
                "You're not in that server.", ephemeral=True
            )
            return

        if not member.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "You need Manage Server permission in that server.", ephemeral=True
            )
            return

        channel = guild.get_channel(int(channel_id))
        if channel is None:
            await interaction.response.send_message(
                "I can't find that channel in that server.", ephemeral=True
            )
            return

        self.settings[str(guild.id)] = channel.id
        storage.save_settings(self.settings)

        await interaction.response.send_message(
            f"Mod log for **{guild.name}** set to {channel.mention}.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
