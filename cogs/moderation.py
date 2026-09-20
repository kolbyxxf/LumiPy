import discord
from discord import app_commands
from discord.ext import commands
from utils.storage import load_data, save_data
from datetime import timedelta

SETTINGS_FILE = "settings.json"

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def mod_log(self, guild, action, moderator, target, reason="No reason"):
        settings = load_data(SETTINGS_FILE)
        channel_id = settings.get(str(guild.id))
        if not channel_id:
            return
        
        channel = guild.get_channel(int(channel_id))
        if not channel:
            return

        embed = discord.Embed(title=action, color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Moderator", value=moderator.mention)
        embed.add_field(name="Target", value=str(target))
        embed.add_field(name="Reason", value=reason, inline=False)
        
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    async def member_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Provides a list of members matching the current input."""
        choices = []
        for member in interaction.guild.members:
            if current.lower() in member.name.lower() or \
               (member.display_name and current.lower() in member.display_name.lower()) or \
               current in str(member.id):
                if len(choices) < 25:
                    choices.append(app_commands.Choice(name=f"{member.display_name} ({member.name})", value=str(member.id)))
        return choices

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(member="The member to kick", reason="The reason for the kick")
    @app_commands.autocomplete(member=member_autocomplete)
    async def kick(self, interaction: discord.Interaction, member: str, reason: str = "No reason"):
        try:
            member_obj = interaction.guild.get_member(int(member))
        except ValueError:
            await interaction.response.send_message("❌ Invalid member ID.", ephemeral=True)
            return

        if not member_obj:
            await interaction.response.send_message("❌ Member not found.", ephemeral=True)
            return
            
        if member_obj == interaction.user:
            await interaction.response.send_message("You cannot kick yourself.", ephemeral=True)
            return
        
        try:
            await member_obj.kick(reason=reason)
            await interaction.response.send_message(f"Kicked {member_obj.display_name}. Reason: {reason}")
            await self.mod_log(interaction.guild, "Member Kicked", interaction.user, member_obj, reason)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to kick this member.", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(member="The member to ban", reason="The reason for the ban")
    @app_commands.autocomplete(member=member_autocomplete)
    async def ban(self, interaction: discord.Interaction, member: str, reason: str = "No reason"):
        try:
            member_obj = interaction.guild.get_member(int(member))
        except ValueError:
            await interaction.response.send_message("❌ Invalid member ID.", ephemeral=True)
            return

        if not member_obj:
            await interaction.response.send_message("❌ Member not found.", ephemeral=True)
            return

        if member_obj == interaction.user:
            await interaction.response.send_message("You cannot ban yourself.", ephemeral=True)
            return

        try:
            await member_obj.ban(reason=reason)
            await interaction.response.send_message(f"Banned {member_obj.display_name}. Reason: {reason}")
            await self.mod_log(interaction.guild, "Member Banned", interaction.user, member_obj, reason)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to ban this member.", ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(member="The member to timeout", minutes="Duration in minutes", reason="The reason for the timeout")
    @app_commands.autocomplete(member=member_autocomplete)
    async def timeout(self, interaction: discord.Interaction, member: str, minutes: int = 60, reason: str = "No reason"):
        try:
            member_obj = interaction.guild.get_member(int(member))
        except ValueError:
            await interaction.response.send_message("❌ Invalid member ID.", ephemeral=True)
            return

        if not member_obj:
            await interaction.response.send_message("❌ Member not found.", ephemeral=True)
            return

        if member_obj.bot:
            await interaction.response.send_message("Cannot timeout bots.", ephemeral=True)
            return

        try:
            duration = discord.utils.utcnow() + timedelta(minutes=minutes)
            await member_obj.timeout(duration, reason=reason)
            await interaction.response.send_message(f"Timed out {member_obj.display_name} for {minutes} minutes.")
            await self.mod_log(interaction.guild, "Member Timed Out", interaction.user, member_obj, reason)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to timeout this member.", ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(member="The member to untimeout")
    @app_commands.autocomplete(member=member_autocomplete)
    async def untimeout(self, interaction: discord.Interaction, member: str):
        try:
            member_obj = interaction.guild.get_member(int(member))
        except ValueError:
            await interaction.response.send_message("❌ Invalid member ID.", ephemeral=True)
            return

        if not member_obj:
            await interaction.response.send_message("❌ Member not found.", ephemeral=True)
            return

        try:
            await member_obj.timeout(None)
            await interaction.response.send_message(f"Removed timeout from {member_obj.display_name}.")
            await self.mod_log(interaction.guild, "Timeout Removed", interaction.user, member_obj)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to do that.", ephemeral=True)

    @app_commands.command(name="purge", description="Delete messages")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        if amount > 100:
            await interaction.response.send_message("Cannot delete more than 100 messages at once.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)

    @app_commands.command(name="setlog", description="Set the moderation log channel")
    @app_commands.default_permissions(manage_guild=True)
    async def setlog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        settings = load_data(SETTINGS_FILE)
        settings[str(interaction.guild.id)] = channel.id
        save_data(SETTINGS_FILE, settings)
        await interaction.response.send_message(f"Mod log set to {channel.mention}.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
