import time
import discord
from discord import app_commands
from discord.ext import commands
from utils import storage
from datetime import timedelta

DEFAULT_AUTO_BAN_WARNINGS, MAX_AUTO_BAN_WARNINGS = 5, 50

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    async def _read_log_channel_id(guild_id: int) -> int | None:
        return await storage.get_log_channel(str(guild_id))

    async def _get_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        channel_id = await self._read_log_channel_id(guild.id)
        if channel_id is None: return None
        channel = guild.get_channel(channel_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    async def _log(self, guild: discord.Guild, text: str) -> None:
        channel = await self._get_log_channel(guild)
        if channel is None: return
        try: await channel.send(text, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException: pass

    @staticmethod
    async def _get_warnings(guild_id: int, user_id: int) -> list[dict]:
        return await storage.get_warnings(str(guild_id), str(user_id))

    @staticmethod
    async def _get_ban_threshold(guild_id: int) -> int:
        return await storage.get_ban_threshold(str(guild_id))

    @staticmethod
    async def _resolve_member(interaction: discord.Interaction, member: str) -> discord.Member | None:
        try: member_obj = interaction.guild.get_member(int(member))
        except ValueError:
            await interaction.response.send_message("❌ Invalid member ID.", ephemeral=True)
            return None
        if not member_obj:
            await interaction.response.send_message("❌ Member not found.", ephemeral=True)
            return None
        return member_obj

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel): 
        await self._log(channel.guild, f"📂 **Channel Created**: {channel.mention}")
        
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel): 
        await self._log(channel.guild, f"🗑️ **Channel Deleted**: #{channel.name} ({channel.id})")
        
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role): 
        await self._log(role.guild, f"➕ **Role Created**: {role.name}")
        
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role): 
        await self._log(role.guild, f"➖ **Role Deleted**: {role.name}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if set(before.roles) != set(after.roles):
            added = [r.name for r in after.roles if r not in before.roles]
            removed = [r.name for r in before.roles if r not in after.roles]
            msg = f"🔄 **Role Update**: {after.mention}"
            if added: msg += f"\n➕ Added: {', '.join(added)}"
            if removed: msg += f"\n➖ Removed: {', '.join(removed)}"
            await self._log(after.guild, msg)

    async def mod_log(self, guild, action, moderator, target, reason="No reason"):
        channel = await self._get_log_channel(guild)
        if channel is None: return
        embed = discord.Embed(title=action, color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Moderator", value=moderator.mention)
        embed.add_field(name="Target", value=str(target))
        embed.add_field(name="Reason", value=(reason or "No reason")[:1024], inline=False)
        try: await channel.send(embed=embed)
        except discord.HTTPException: pass

    async def member_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        choices = []
        for member in interaction.guild.members:
            if current.lower() in member.name.lower() or (member.display_name and current.lower() in member.display_name.lower()) or current in str(member.id):
                if len(choices) < 25: choices.append(app_commands.Choice(name=f"{member.display_name} ({member.name})", value=str(member.id)))
        return choices

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only()
    @app_commands.autocomplete(member=member_autocomplete)
    async def kick(self, interaction: discord.Interaction, member: str, reason: str = "No reason"):
        member_obj = await self._resolve_member(interaction, member)
        if not member_obj or member_obj == interaction.user: return
        try:
            await member_obj.kick(reason=reason)
            await interaction.response.send_message(f"Kicked {member_obj.display_name}. Reason: {reason}")
            await self.mod_log(interaction.guild, "Member Kicked", interaction.user, member_obj, reason)
        except discord.Forbidden: await interaction.response.send_message("I don't have permission.", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    @app_commands.autocomplete(member=member_autocomplete)
    async def ban(self, interaction: discord.Interaction, member: str, reason: str = "No reason"):
        member_obj = await self._resolve_member(interaction, member)
        if not member_obj or member_obj == interaction.user: return
        try:
            await member_obj.ban(reason=reason)
            await interaction.response.send_message(f"Banned {member_obj.display_name}. Reason: {reason}")
            await self.mod_log(interaction.guild, "Member Banned", interaction.user, member_obj, reason)
        except discord.Forbidden: await interaction.response.send_message("I don't have permission.", ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.autocomplete(member=member_autocomplete)
    async def timeout(self, interaction: discord.Interaction, member: str, minutes: int = 60, reason: str = "No reason"):
        member_obj = await self._resolve_member(interaction, member)
        if not member_obj or member_obj.bot: return
        try:
            await member_obj.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=reason)
            await interaction.response.send_message(f"Timed out {member_obj.display_name} for {minutes} minutes.")
            await self.mod_log(interaction.guild, "Member Timed Out", interaction.user, member_obj, reason)
        except discord.Forbidden: await interaction.response.send_message("I don't have permission.", ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.autocomplete(member=member_autocomplete)
    async def untimeout(self, interaction: discord.Interaction, member: str):
        member_obj = await self._resolve_member(interaction, member)
        if not member_obj: return
        try:
            await member_obj.timeout(None)
            await interaction.response.send_message(f"Removed timeout from {member_obj.display_name}.")
            await self.mod_log(interaction.guild, "Timeout Removed", interaction.user, member_obj)
        except discord.Forbidden: await interaction.response.send_message("I don't have permission.", ephemeral=True)

    @app_commands.command(name="purge", description="Delete messages")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def purge(self, interaction: discord.Interaction, amount: int):
        if amount > 100: return await interaction.response.send_message("Cannot delete more than 100 messages.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)

    @app_commands.command(name="setlog", description="Set the moderation log channel")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def setlog(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await storage.set_log_channel(str(interaction.guild.id), channel.id)
        await interaction.response.send_message(f"Mod log set to {channel.mention}.", ephemeral=True)

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.autocomplete(member=member_autocomplete)
    async def warn(self, interaction: discord.Interaction, member: str, reason: str = "No reason"):
        member_obj = await self._resolve_member(interaction, member)
        if not member_obj or member_obj == interaction.user or member_obj.bot: return
        if interaction.user.id != interaction.guild.owner_id and member_obj.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("❌ You can't warn someone with an equal or higher role.", ephemeral=True)

        reason = reason[:500]
        warns = await self._get_warnings(interaction.guild.id, member_obj.id)
        warn_id = max((w.get("id", 0) for w in warns), default=0) + 1
        new_warn = {"id": warn_id, "moderator_id": interaction.user.id, "reason": reason, "timestamp": int(time.time())}
        
        await interaction.response.defer()
        await storage.add_warning(str(interaction.guild.id), str(member_obj.id), new_warn)
        warns.append(new_warn)

        ban_threshold = await self._get_ban_threshold(interaction.guild.id)
        should_ban = ban_threshold > 0 and len(warns) >= ban_threshold

        dm_text = f"⚠️ You were warned in **{interaction.guild.name}**.\nReason: {reason}"
        if should_ban: dm_text += f"\nYou have reached {ban_threshold} warnings and are being banned."
        
        dm_sent = True
        try: await member_obj.send(dm_text)
        except discord.HTTPException: dm_sent = False
        note = "" if dm_sent else "\n(I couldn't DM them.)"
        message = f"⚠️ Warned {member_obj.display_name} (warning #{warn_id}, {len(warns)} total). Reason: {reason}{note}"
        
        await self.mod_log(interaction.guild, "Member Warned", interaction.user, member_obj, f"{reason} (warning #{warn_id}, {len(warns)} total)")

        if should_ban:
            try:
                await member_obj.ban(reason=f"Auto-ban: reached {ban_threshold} warnings")
                await self.mod_log(interaction.guild, "Member Auto-Banned", self.bot.user, member_obj, f"Reached {ban_threshold} warnings")
                message += f"\n🔨 {member_obj.display_name} reached {ban_threshold} warnings and was banned automatically."
            except discord.HTTPException:
                message += f"\n❌ They reached {ban_threshold} warnings but I couldn't ban them."
        await interaction.followup.send(message)

    @app_commands.command(name="warnings", description="View a member's warnings")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.autocomplete(member=member_autocomplete)
    async def warnings_cmd(self, interaction: discord.Interaction, member: str):
        member_obj = await self._resolve_member(interaction, member)
        if not member_obj: return
        warns = await self._get_warnings(interaction.guild.id, member_obj.id)
        if not warns: return await interaction.response.send_message(f"{member_obj.display_name} has no warnings.", ephemeral=True)
        
        recent = warns[-10:]
        lines = [f"**#{w.get('id', '?')}** • <t:{int(w.get('timestamp', 0))}:R> • by <@{w.get('moderator_id', 0)}>\n{str(w.get('reason', 'No reason'))[:100]}" for w in reversed(recent)]
        embed = discord.Embed(title=f"⚠️ Warnings for {member_obj.display_name}", description="\n".join(lines), color=discord.Color.orange())
        embed.set_footer(text=f"Showing the latest {len(recent)} of {len(warns)} warnings" if len(warns) > len(recent) else f"{len(warns)} total")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="delwarn", description="Remove one warning from a member")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.autocomplete(member=member_autocomplete)
    async def delwarn(self, interaction: discord.Interaction, member: str, warn_id: int):
        member_obj = await self._resolve_member(interaction, member)
        if not member_obj: return
        warns = await self._get_warnings(interaction.guild.id, member_obj.id)
        if not any(w.get("id") == warn_id for w in warns):
            return await interaction.response.send_message(f"❌ No warning #{warn_id} found.", ephemeral=True)
        
        await storage.remove_warning(str(interaction.guild.id), str(member_obj.id), warn_id)
        await interaction.response.send_message(f"🗑️ Removed warning #{warn_id} from {member_obj.display_name}.")
        await self.mod_log(interaction.guild, "Warning Removed", interaction.user, member_obj, f"Removed warning #{warn_id}")

    @app_commands.command(name="clearwarnings", description="Clear all of a member's warnings")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.autocomplete(member=member_autocomplete)
    async def clearwarnings(self, interaction: discord.Interaction, member: str):
        member_obj = await self._resolve_member(interaction, member)
        if not member_obj: return
        warns = await self._get_warnings(interaction.guild.id, member_obj.id)
        if not warns: return await interaction.response.send_message(f"{member_obj.display_name} has no warnings.", ephemeral=True)
        
        await storage.clear_warnings(str(interaction.guild.id), str(member_obj.id))
        await interaction.response.send_message(f"🧹 Cleared {len(warns)} warning(s) from {member_obj.display_name}.")
        await self.mod_log(interaction.guild, "Warnings Cleared", interaction.user, member_obj, f"Cleared {len(warns)} warning(s)")

    @app_commands.command(name="warnlimit", description="View or change how many warnings lead to an automatic ban")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.describe(limit="Warnings before an automatic ban (0 turns it off). Leave empty to view.")
    async def warnlimit(self, interaction: discord.Interaction, limit: int | None = None):
        current = await self._get_ban_threshold(interaction.guild.id)
        if limit is None:
            text = "Automatic bans are **off**." if current == 0 else f"Members are banned automatically at **{current}** warnings."
            return await interaction.response.send_message(text, ephemeral=True)
        if limit < 0 or limit > MAX_AUTO_BAN_WARNINGS:
            return await interaction.response.send_message(f"❌ Choose a number from 0 to {MAX_AUTO_BAN_WARNINGS}.", ephemeral=True)
        
        await storage.set_ban_threshold(str(interaction.guild.id), limit)
        text = "🔓 Automatic bans are now **off**." if limit == 0 else f"🔧 Members will now be banned automatically at **{limit}** warnings."
        await interaction.response.send_message(text, ephemeral=True)
        
        old_text = "off" if current == 0 else f"{current} warnings"
        new_text = "off" if limit == 0 else f"{limit} warnings"
        await self.mod_log(interaction.guild, "Warn Limit Changed", interaction.user, interaction.user, f"Automatic ban changed from {old_text} to {new_text}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))