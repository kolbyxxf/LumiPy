import re
import time
from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
import discord
from discord import app_commands
from discord.ext import commands
from utils import storage

STRIKE_RESET_SECONDS = 1800
MAX_KEYWORD_LENGTH = 50
MAX_KEYWORDS = 100
INVITE_PATTERN = re.compile(r"(?:discord\.gg|discordapp\.com/invite|discord\.com/invite)/[a-zA-Z0-9]+", re.IGNORECASE)

DEFAULT_CONFIG = {
    "spam_threshold": 5, "spam_window": 10, "mention_limit": 5,
    "invites_blocked": True, "keywords": [],
    "escalation": {"warn_after": 2, "mute_after": 4, "kick_after": 6},
}

@lru_cache(maxsize=512)
def _keyword_pattern(keyword: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(keyword)}(?!\w)", re.IGNORECASE)

class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._strikes: dict[int, dict[int, dict]] = defaultdict(dict)
        self._spam_tracker: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

    def _default_config(self) -> dict: return deepcopy(DEFAULT_CONFIG)

    async def _get_config(self, guild_id: int) -> dict:
        config = await storage.get_automod_config(str(guild_id))
        if not isinstance(config, dict):
            config = self._default_config()
            await storage.set_automod_config(str(guild_id), config)
            return config

        changed = False
        integer_defaults = {"spam_threshold": 5, "spam_window": 10, "mention_limit": 5}
        for key, default in integer_defaults.items():
            value = config.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                config[key] = default; changed = True

        if not isinstance(config.get("invites_blocked"), bool):
            config["invites_blocked"] = True; changed = True

        keywords = config.get("keywords")
        if not isinstance(keywords, list):
            config["keywords"] = []; changed = True
        else:
            cleaned = [k.strip().lower() for k in keywords if isinstance(k, str) and k.strip() and len(k.strip()) <= MAX_KEYWORD_LENGTH]
            cleaned = list(dict.fromkeys(cleaned))[:MAX_KEYWORDS]
            if cleaned != keywords: config["keywords"] = cleaned; changed = True

        escalation = config.get("escalation")
        if not isinstance(escalation, dict):
            config["escalation"] = deepcopy(DEFAULT_CONFIG["escalation"]); changed = True
            escalation = config["escalation"]
        
        for key, default in DEFAULT_CONFIG["escalation"].items():
            value = escalation.get(key)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                escalation[key] = default; changed = True

        if escalation["mute_after"] < escalation["warn_after"]:
            escalation["mute_after"] = max(escalation["warn_after"], 4); changed = True
        if escalation["kick_after"] < escalation["mute_after"]:
            escalation["kick_after"] = max(escalation["mute_after"], 6); changed = True

        if changed: await storage.set_automod_config(str(guild_id), config)
        return config

    async def _save_config(self, guild_id: int, config: dict) -> None:
        await storage.set_automod_config(str(guild_id), config)

    async def _log_action(self, guild: discord.Guild, action: str, target: discord.Member, reason: str):
        try:
            mod_cog = self.bot.get_cog("Moderation")
            if mod_cog and hasattr(mod_cog, "mod_log"):
                await mod_cog.mod_log(guild, action, self.bot.user, target, reason)
        except Exception: pass

    def _add_strike(self, guild_id: int, user_id: int) -> int:
        now = time.time()
        user_strikes = self._strikes[guild_id].setdefault(user_id, {"strikes": 0, "last_reset": now})
        if now - user_strikes["last_reset"] > STRIKE_RESET_SECONDS: user_strikes["strikes"] = 0
        user_strikes["strikes"] += 1
        user_strikes["last_reset"] = now
        return user_strikes["strikes"]

    async def _apply_escalation(self, guild: discord.Guild, member: discord.Member, strikes: int, reason: str):
        config = await self._get_config(guild.id)
        escalation = config["escalation"]

        if strikes >= escalation["kick_after"]:
            try:
                await member.kick(reason=f"AutoMod: {reason} ({strikes} strikes)")
                self._strikes[guild.id].pop(member.id, None)
                self._spam_tracker[guild.id].pop(member.id, None)
                await self._log_action(guild, "👢 AUTO-KICK", member, f"{reason} | Strikes: {strikes}")
            except discord.Forbidden:
                await self._log_action(guild, "❌ AUTO-KICK FAILED", member, "Missing permissions")
            except discord.HTTPException: pass
            return

        if strikes >= escalation["mute_after"]:
            mute_role = discord.utils.get(guild.roles, name="Muted")
            if not mute_role or mute_role >= guild.me.top_role: return
            try:
                if mute_role not in member.roles:
                    await member.add_roles(mute_role, reason=f"AutoMod: {reason} ({strikes} strikes)")
                    await self._log_action(guild, "🔇 AUTO-MUTE", member, f"{reason} | Strikes: {strikes}")
            except discord.Forbidden: pass
            except discord.HTTPException: pass
            return

        if strikes >= escalation["warn_after"]:
            try:
                mod_cog = self.bot.get_cog("Moderation")
                if mod_cog and hasattr(mod_cog, "_add_warning_legacy"):
                    await mod_cog._add_warning_legacy(member, self.bot.user, f"AutoMod: {reason}")
                await self._log_action(guild, "⚠️ AUTO-WARN", member, f"{reason} | Strikes: {strikes}")
            except Exception: pass

    async def _scan_message(self, message: discord.Message, *, check_spam: bool) -> None:
        if message.author.bot or not message.guild or not isinstance(message.author, discord.Member): return
        if message.author.guild_permissions.manage_messages: return
        
        guild = message.guild
        config = await self._get_config(guild.id)
        triggered_reasons: list[str] = []

        if config["invites_blocked"] and INVITE_PATTERN.search(message.content):
            triggered_reasons.append("Discord invite link detected")

        for keyword in config["keywords"]:
            if _keyword_pattern(keyword).search(message.content):
                triggered_reasons.append(f"Banned keyword: '{keyword}'")
                break

        if len(message.mentions) + len(message.role_mentions) > config["mention_limit"]:
            triggered_reasons.append(f"Mention spam")

        if check_spam:
            now = time.time()
            window = config["spam_window"]
            threshold = config["spam_threshold"]
            timestamps = self._spam_tracker[guild.id][message.author.id]
            timestamps[:] = [t for t in timestamps if now - t < window]
            timestamps.append(now)
            if len(timestamps) > threshold:
                triggered_reasons.append(f"Message spam")
                timestamps.clear()

        if not triggered_reasons: return
        
        try: await message.delete()
        except discord.HTTPException: pass

        strikes = self._add_strike(guild.id, message.author.id)
        await self._apply_escalation(guild, message.author, strikes, "; ".join(triggered_reasons))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message): await self._scan_message(message, check_spam=True)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content == after.content: return
        await self._scan_message(after, check_spam=False)

    @app_commands.command(name="automod", description="Configure AutoMod settings")
    @app_commands.describe(setting="The setting to configure", value="New value, keyword, or number")
    @app_commands.choices(setting=[
        app_commands.Choice(name="Show Config", value="show"),
        app_commands.Choice(name="Toggle Invites", value="toggle_invites"),
        app_commands.Choice(name="Set Spam Threshold", value="spam_threshold"),
        app_commands.Choice(name="Set Mention Limit", value="mention_limit"),
        app_commands.Choice(name="Add Keyword", value="add_keyword"),
        app_commands.Choice(name="Remove Keyword", value="remove_keyword"),
        app_commands.Choice(name="List Keywords", value="list_keywords"),
        app_commands.Choice(name="Reset Strikes", value="reset_strikes"),
    ])
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def automod_cmd(self, interaction: discord.Interaction, setting: app_commands.Choice[str], value: str | None = None):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Need **Manage Server**.", ephemeral=True)

        guild_id = interaction.guild.id
        config = await self._get_config(guild_id)
        embed = discord.Embed(title="⚙️ AutoMod Configuration", color=discord.Color.blurple())

        if setting.value == "show":
            embed.description = (f"**Invites Blocked:** {'✅' if config['invites_blocked'] else '❌'}\n"
                                 f"**Spam Threshold:** {config['spam_threshold']} msgs / {config['spam_window']}s\n"
                                 f"**Mention Limit:** {config['mention_limit']}\n"
                                 f"**Keywords:** {len(config['keywords'])} active\n"
                                 f"**Escalation:** Warn@{config['escalation']['warn_after']} | Mute@{config['escalation']['mute_after']} | Kick@{config['escalation']['kick_after']}")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if setting.value == "toggle_invites":
            config["invites_blocked"] = not config["invites_blocked"]
            await self._save_config(guild_id, config)
            embed.description = f"Invite filtering is now **{'enabled' if config['invites_blocked'] else 'disabled'}**."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if setting.value in ("spam_threshold", "mention_limit"):
            if not value: return await interaction.response.send_message("❌ Provide a number.", ephemeral=True)
            try:
                val = int(value)
                if val <= 0: raise ValueError
            except ValueError: return await interaction.response.send_message("❌ Positive whole number only.", ephemeral=True)
            key = "spam_threshold" if setting.value == "spam_threshold" else "mention_limit"
            config[key] = val
            await self._save_config(guild_id, config)
            embed.description = f"**{key.replace('_', ' ').title()}** set to `{val}`."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if setting.value == "add_keyword":
            if not value or not value.strip(): return await interaction.response.send_message("❌ Provide a keyword.", ephemeral=True)
            keyword = value.strip().lower()
            if len(keyword) > MAX_KEYWORD_LENGTH: return await interaction.response.send_message(f"❌ Max {MAX_KEYWORD_LENGTH} chars.", ephemeral=True)
            if keyword in config["keywords"]: return await interaction.response.send_message("⚠️ Already exists.", ephemeral=True)
            if len(config["keywords"]) >= MAX_KEYWORDS: return await interaction.response.send_message(f"❌ Max {MAX_KEYWORDS} keywords.", ephemeral=True)
            config["keywords"].append(keyword)
            await self._save_config(guild_id, config)
            return await interaction.response.send_message(f"✅ Added: `{keyword}`", ephemeral=True)

        if setting.value == "remove_keyword":
            if not value or not value.strip(): return await interaction.response.send_message("❌ Provide a keyword.", ephemeral=True)
            keyword = value.strip().lower()
            if keyword in config["keywords"]:
                config["keywords"].remove(keyword)
                await self._save_config(guild_id, config)
                return await interaction.response.send_message(f"🗑️ Removed: `{keyword}`", ephemeral=True)
            return await interaction.response.send_message("❌ Not found.", ephemeral=True)

        if setting.value == "list_keywords":
            keywords = config["keywords"]
            embed.description = "\n".join(f"`{k[:MAX_KEYWORD_LENGTH]}`" for k in keywords[:20]) if keywords else "No keywords configured."
            if len(keywords) > 20: embed.set_footer(text=f"...and {len(keywords) - 20} more")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if setting.value == "reset_strikes":
            self._strikes.pop(guild_id, None)
            self._spam_tracker.pop(guild_id, None)
            embed.description = "✅ All strike counters reset."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed.description = "❌ Invalid command usage."
        embed.color = discord.Color.red()
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoMod(bot))