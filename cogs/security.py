import re
import time
from collections import defaultdict
from copy import deepcopy
import discord
from discord import app_commands
from discord.ext import commands, tasks
from utils import storage

DEFAULT_SECURITY_CONFIG = {
    "anti_nuke": True, "anti_raid": True, "anti_invite": False,
    "invite_exempt_channels": [], "lockdown_threshold": 10, "join_window": 30,
    "max_channels_per_min": 5, "max_roles_per_min": 5,
    "quarantine_role_name": "Quarantined", "trusted_roles": [],
}

INVITE_RE = re.compile(r"(?<![\w.-])(?:https?://)?(?:www\.)?(?:discord\.gg|discord(?:app)?\.com/invite)/(?P<code>[a-z0-9-]{2,32})", re.IGNORECASE)

def find_invites(text: str) -> list[dict]:
    seen, results = set(), []
    for m in INVITE_RE.finditer(text):
        code = m.group("code")
        if code.lower() not in seen:
            seen.add(code.lower())
            results.append({"url": m.group(0), "code": code})
    return results

class Security(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._channel_tracker: dict[int, list[tuple[int, float]]] = defaultdict(list)
        self._role_tracker: dict[int, list[tuple[int, float]]] = defaultdict(list)
        self._join_tracker: dict[int, list[tuple[int, float]]] = defaultdict(list)
        self._active_lockdowns: dict[int, bool] = {}
        self._lockdown_quarantined: dict[int, set[int]] = defaultdict(set)
        self.auto_check.start()

    def _default_config(self) -> dict: return deepcopy(DEFAULT_SECURITY_CONFIG)

    async def _get_config(self, guild_id: int) -> dict:
        config = await storage.get_security_config(str(guild_id))
        if not isinstance(config, dict):
            config = self._default_config()
            await storage.set_security_config(str(guild_id), config)
            return config

        changed = False
        for key, default_value in DEFAULT_SECURITY_CONFIG.items():
            if key not in config:
                config[key] = deepcopy(default_value)
                changed = True
        for list_key in ("trusted_roles", "invite_exempt_channels"):
            if not isinstance(config.get(list_key), list):
                config[list_key] = []
                changed = True
        if changed: await storage.set_security_config(str(guild_id), config)
        return config

    async def _save_config(self, guild_id: int, config: dict) -> None:
        await storage.set_security_config(str(guild_id), config)

    async def _log_action(self, guild: discord.Guild, action: str, target: discord.Member | None, reason: str):
        try:
            mod_cog = self.bot.get_cog("Moderation")
            if mod_cog and hasattr(mod_cog, "mod_log"): await mod_cog.mod_log(guild, action, self.bot.user, target or guild.me, reason)
        except Exception: pass

    def _is_trusted(self, member: discord.Member, config: dict) -> bool:
        if member.id == member.guild.owner_id: return True
        trusted_roles = {int(role_id) for role_id in config.get("trusted_roles", []) if str(role_id).isdigit()}
        return any(role.id in trusted_roles for role in member.roles)

    async def _ensure_quarantine_role(self, guild: discord.Guild) -> discord.Role | None:
        config = await self._get_config(guild.id)
        role = discord.utils.get(guild.roles, name=config["quarantine_role_name"])
        if role: return role
        try:
            return await guild.create_role(name=config["quarantine_role_name"], permissions=discord.Permissions.none(), reason="Security: Creating quarantine role")
        except (discord.Forbidden, discord.HTTPException): return None

    async def _apply_quarantine(self, member: discord.Member, reason: str) -> bool:
        if member.bot and member.id == self.bot.user.id: return False
        role = await self._ensure_quarantine_role(member.guild)
        if not role or role >= member.guild.me.top_role: return False
        if role in member.roles: return True
        try:
            await member.add_roles(role, reason=f"Security: {reason}")
            await self._log_action(member.guild, "🔒 QUARANTINED", member, reason)
            return True
        except (discord.Forbidden, discord.HTTPException): return False

    async def _remove_quarantine(self, member: discord.Member, reason: str = "Manual release") -> bool:
        config = await self._get_config(member.guild.id)
        role = discord.utils.get(member.guild.roles, name=config["quarantine_role_name"])
        if not role or role not in member.roles: return True
        try:
            await member.remove_roles(role, reason=f"Security: {reason}")
            await self._log_action(member.guild, "🔓 UNQUARANTINED", member, reason)
            return True
        except (discord.Forbidden, discord.HTTPException): return False

    async def _get_audit_actor(self, guild: discord.Guild, action: discord.AuditLogAction, target_id: int) -> discord.Member | None:
        try:
            async for entry in guild.audit_logs(limit=5, action=action):
                if entry.target and getattr(entry.target, "id", None) == target_id and entry.created_at.timestamp() >= time.time() - 15:
                    return entry.user
        except (discord.Forbidden, discord.HTTPException): pass
        return None

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        config = await self._get_config(channel.guild.id)
        if not config["anti_nuke"]: return
        actor = await self._get_audit_actor(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        if actor is None or actor.id == self.bot.user.id or self._is_trusted(actor, config): return
        
        now = time.time()
        tracker = self._channel_tracker[channel.guild.id]
        tracker.append((actor.id, now))
        tracker[:] = [(aid, ts) for aid, ts in tracker if ts > now - 60]
        
        if sum(1 for aid, _ in tracker if aid == actor.id) > config["max_channels_per_min"]:
            await self._apply_quarantine(actor, f"Anti-nuke: Mass channel creation")
            try: await channel.delete(reason="Security: Anti-nuke")
            except (discord.Forbidden, discord.HTTPException): pass

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        config = await self._get_config(role.guild.id)
        if not config["anti_nuke"]: return
        actor = await self._get_audit_actor(role.guild, discord.AuditLogAction.role_create, role.id)
        if actor is None or actor.id == self.bot.user.id or self._is_trusted(actor, config): return
        
        now = time.time()
        tracker = self._role_tracker[role.guild.id]
        tracker.append((actor.id, now))
        tracker[:] = [(aid, ts) for aid, ts in tracker if ts > now - 60]
        
        if sum(1 for aid, _ in tracker if aid == actor.id) > config["max_roles_per_min"]:
            await self._apply_quarantine(actor, f"Anti-nuke: Mass role creation")
            try: await role.delete(reason="Security: Anti-nuke")
            except (discord.Forbidden, discord.HTTPException): pass

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        config = await self._get_config(after.id)
        if not config["anti_nuke"]: return
        changes = []
        if before.icon != after.icon: changes.append("Server icon changed")
        if before.name != after.name: changes.append("Server name changed")
        if before.owner_id != after.owner_id: changes.append("Ownership transferred")
        if changes:
            actor = await self._get_audit_actor(after, discord.AuditLogAction.guild_update, after.id) if before.owner_id != after.owner_id else None
            await self._log_action(after, "🚨 GUILD UPDATE", actor, "; ".join(changes))

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        config = await self._get_config(after.guild.id)
        if not config["anti_nuke"] or self._is_trusted(after, config): return
        dangerous = ("administrator", "manage_guild", "ban_members", "kick_members", "manage_roles", "manage_channels")
        gained = [p for p in dangerous if getattr(after.guild_permissions, p, False) and not getattr(before.guild_permissions, p, False)]
        if gained:
            await self._apply_quarantine(after, f"Dangerous permissions granted: {', '.join(gained)}")
            await self._log_action(after.guild, "🚨 PERMISSION ESCALATION", after, f"Gained: {', '.join(gained)}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        config = await self._get_config(guild.id)
        if self._active_lockdowns.get(guild.id, False):
            if await self._apply_quarantine(member, "Active raid lockdown"):
                self._lockdown_quarantined[guild.id].add(member.id)
            return
        if not config["anti_raid"]: return
        
        now = time.time()
        tracker = self._join_tracker[guild.id]
        tracker.append((member.id, now))
        tracker[:] = [(mid, ts) for mid, ts in tracker if ts > now - config["join_window"]]
        
        if len(tracker) >= config["lockdown_threshold"] and not self._active_lockdowns.get(guild.id, False):
            self._active_lockdowns[guild.id] = True
            await self._log_action(guild, "🚨 RAID LOCKDOWN", None, f"{len(tracker)} joins in {config['join_window']}s")
            for mid, _ in tracker:
                m = guild.get_member(mid)
                if m and await self._apply_quarantine(m, "Raid lockdown"):
                    self._lockdown_quarantined[guild.id].add(m.id)

    async def _check_invites(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot or not isinstance(message.author, discord.Member): return
        config = await self._get_config(message.guild.id)
        if not config["anti_invite"] or self._is_trusted(message.author, config) or message.author.guild_permissions.manage_messages: return
        
        exempt = {int(cid) for cid in config.get("invite_exempt_channels", []) if str(cid).isdigit()}
        location_ids = {message.channel.id, getattr(message.channel, "parent_id", None), getattr(message.channel, "category_id", None)}
        if exempt & location_ids: return
        
        invites = find_invites(message.content)
        if not invites: return
        
        try: await message.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException): return
        
        await self._log_action(message.guild, "🔗 INVITE BLOCKED", message.author, f"Discord invite in #{message.channel.name}")
        try: await message.channel.send(f"{message.author.mention}, Discord invite links aren't allowed here.", delete_after=5)
        except (discord.Forbidden, discord.HTTPException): pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message): await self._check_invites(message)
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content != after.content: await self._check_invites(after)

    @tasks.loop(minutes=5)
    async def auto_check(self):
        now = time.time()
        for guild_id in list(self._active_lockdowns):
            if not self._active_lockdowns.get(guild_id): continue
            guild = self.bot.get_guild(guild_id)
            if not guild:
                self._active_lockdowns.pop(guild_id, None)
                self._lockdown_quarantined.pop(guild_id, None)
                continue
            
            recent = self._join_tracker[guild_id]
            recent[:] = [(mid, ts) for mid, ts in recent if ts > now - 600]
            config = await self._get_config(guild_id)
            if len(recent) >= config["lockdown_threshold"]: continue
            
            self._active_lockdowns[guild_id] = False
            await self._log_action(guild, "✅ LOCKDOWN LIFTED", None, "No suspicious activity for 10 min")
            
            for mid in self._lockdown_quarantined.pop(guild_id, set()):
                member = guild.get_member(mid)
                if member: await self._remove_quarantine(member, "Lockdown lifted")

    @auto_check.before_loop
    async def before_auto_check(self): await self.bot.wait_until_ready()

    @app_commands.command(name="security", description="Configure security settings")
    @app_commands.describe(setting="Setting to configure", role="Role for trusted/add/remove", member="Member for quarantine", channel="Channel for invite-exempt", value="Numeric value")
    @app_commands.choices(setting=[
        app_commands.Choice(name="Show Config", value="show"), app_commands.Choice(name="Toggle Anti-Nuke", value="toggle_anti_nuke"),
        app_commands.Choice(name="Toggle Anti-Raid", value="toggle_anti_raid"), app_commands.Choice(name="Toggle Anti-Invite", value="toggle_anti_invite"),
        app_commands.Choice(name="Add Invite-Exempt Channel", value="add_invite_channel"), app_commands.Choice(name="Remove Invite-Exempt Channel", value="remove_invite_channel"),
        app_commands.Choice(name="Set Lockdown Threshold", value="set_lockdown_threshold"), app_commands.Choice(name="Add Trusted Role", value="add_trusted_role"),
        app_commands.Choice(name="Remove Trusted Role", value="remove_trusted_role"), app_commands.Choice(name="Force Lockdown", value="force_lockdown"),
        app_commands.Choice(name="Release Lockdown", value="release_lockdown"), app_commands.Choice(name="Quarantine Member", value="quarantine"),
        app_commands.Choice(name="Unquarantine Member", value="unquarantine"),
    ])
    @app_commands.default_permissions(manage_guild=True)
    async def security_cmd(self, interaction: discord.Interaction, setting: app_commands.Choice[str], role: discord.Role | None = None, member: discord.Member | None = None, channel: discord.abc.GuildChannel | None = None, value: str | None = None):
        guild = interaction.guild
        if guild is None: return await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
        
        config = await self._get_config(guild.id)
        embed = discord.Embed(title="🛡️ Security Configuration", color=discord.Color.blurple())

        if setting.value == "show":
            embed.description = (f"**Anti-Nuke:** {'🟢 Enabled' if config['anti_nuke'] else '🔴 Disabled'}\n"
                                 f"**Anti-Raid:** {'🟢 Enabled' if config['anti_raid'] else '🔴 Disabled'}\n"
                                 f"**Anti-Invite:** {'🟢 Enabled' if config['anti_invite'] else '🔴 Disabled'}\n"
                                 f"**Invite-Exempt Channels:** {', '.join(f'<#{c}>' for c in config['invite_exempt_channels']) or '`None`'}\n"
                                 f"**Lockdown Threshold:** `{config['lockdown_threshold']}` joins / `{config['join_window']}`s\n"
                                 f"**Active Lockdown:** {'🔴 YES' if self._active_lockdowns.get(guild.id, False) else '🟢 NO'}")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if setting.value == "toggle_anti_nuke":
            config["anti_nuke"] = not config["anti_nuke"]
            await self._save_config(guild.id, config)
            return await interaction.response.send_message(f"Anti-nuke is now **{'enabled' if config['anti_nuke'] else 'disabled'}**.", ephemeral=True)
        if setting.value == "toggle_anti_raid":
            config["anti_raid"] = not config["anti_raid"]
            await self._save_config(guild.id, config)
            return await interaction.response.send_message(f"Anti-raid is now **{'enabled' if config['anti_raid'] else 'disabled'}**.", ephemeral=True)
        if setting.value == "toggle_anti_invite":
            config["anti_invite"] = not config["anti_invite"]
            await self._save_config(guild.id, config)
            return await interaction.response.send_message(f"Anti-invite is now **{'enabled' if config['anti_invite'] else 'disabled'}**.", ephemeral=True)

        if setting.value == "set_lockdown_threshold":
            if value is None: return await interaction.response.send_message("❌ Please provide a numeric value.", ephemeral=True)
            try: threshold = int(value)
            except ValueError: return await interaction.response.send_message("❌ Please provide a valid whole number.", ephemeral=True)
            if threshold < 1: return await interaction.response.send_message("❌ Lockdown threshold must be at least `1`.", ephemeral=True)
            config["lockdown_threshold"] = threshold
            await self._save_config(guild.id, config)
            return await interaction.response.send_message(f"🔧 Lockdown threshold set to `{threshold}` joins.", ephemeral=True)

        if setting.value == "add_trusted_role":
            if role is None: return await interaction.response.send_message("❌ Please specify a role.", ephemeral=True)
            if role.id not in config["trusted_roles"]:
                config["trusted_roles"].append(role.id)
                await self._save_config(guild.id, config)
                return await interaction.response.send_message(f"✅ Added {role.mention} as a trusted role.", ephemeral=True)
            return await interaction.response.send_message(f"⚠️ {role.mention} is already trusted.", ephemeral=True)

        if setting.value == "remove_trusted_role":
            if role is None: return await interaction.response.send_message("❌ Please specify a role.", ephemeral=True)
            if role.id in config["trusted_roles"]:
                config["trusted_roles"].remove(role.id)
                await self._save_config(guild.id, config)
                return await interaction.response.send_message(f"🗑️ Removed {role.mention} from trusted roles.", ephemeral=True)
            return await interaction.response.send_message(f"⚠️ {role.mention} is not in the trusted list.", ephemeral=True)

        if setting.value == "add_invite_channel":
            if channel is None: return await interaction.response.send_message("❌ Please specify a channel.", ephemeral=True)
            if channel.id not in config["invite_exempt_channels"]:
                config["invite_exempt_channels"].append(channel.id)
                await self._save_config(guild.id, config)
                return await interaction.response.send_message(f"✅ Invites are now allowed in {channel.mention}.", ephemeral=True)
            return await interaction.response.send_message(f"⚠️ {channel.mention} is already exempt.", ephemeral=True)

        if setting.value == "remove_invite_channel":
            if channel is None: return await interaction.response.send_message("❌ Please specify a channel.", ephemeral=True)
            if channel.id in config["invite_exempt_channels"]:
                config["invite_exempt_channels"].remove(channel.id)
                await self._save_config(guild.id, config)
                return await interaction.response.send_message(f"🗑️ Invites are blocked again in {channel.mention}.", ephemeral=True)
            return await interaction.response.send_message(f"⚠️ {channel.mention} is not in the exempt list.", ephemeral=True)

        if setting.value == "force_lockdown":
            self._active_lockdowns[guild.id] = True
            await self._log_action(guild, "🛑 MANUAL LOCKDOWN", None, f"Triggered by {interaction.user}")
            return await interaction.response.send_message("🔴 Manual lockdown activated.\nAll new members will be quarantined.", ephemeral=True)

        if setting.value == "release_lockdown":
            self._active_lockdowns[guild.id] = False
            await self._log_action(guild, "✅ MANUAL RELEASE", None, f"Lockdown lifted by {interaction.user}")
            for mid in self._lockdown_quarantined.pop(guild.id, set()):
                target = guild.get_member(mid)
                if target: await self._remove_quarantine(target, "Manual lockdown release")
            return await interaction.response.send_message("🟢 Lockdown released.\nMembers quarantined by the lockdown have been released.", ephemeral=True)

        if setting.value == "quarantine":
            if member is None: return await interaction.response.send_message("❌ Please specify a member.", ephemeral=True)
            success = await self._apply_quarantine(member, f"Manual quarantine by {interaction.user}")
            return await interaction.response.send_message(f"🔒 {member.mention} has been quarantined." if success else f"❌ Failed to quarantine {member.mention}.", ephemeral=True)

        if setting.value == "unquarantine":
            if member is None: return await interaction.response.send_message("❌ Please specify a member.", ephemeral=True)
            success = await self._remove_quarantine(member, f"Manual unquarantine by {interaction.user}")
            return await interaction.response.send_message(f"🔓 {member.mention} has been unquarantined." if success else f"❌ Failed to unquarantine {member.mention}.", ephemeral=True)

        return await interaction.response.send_message("❌ Invalid security setting.", ephemeral=True)

    def cog_unload(self):
        self.auto_check.cancel()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Security(bot))