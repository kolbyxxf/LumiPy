import math
import random
import time
import discord
from discord import app_commands
from discord.ext import commands
from utils import storage

XP_MIN, XP_MAX, XP_COOLDOWN_SECONDS, XP_PER_LEVEL, MAX_REWARD_LEVEL = 15, 25, 60, 100, 1000
BAR_LENGTH, BAR_FILLED, BAR_EMPTY = 10, "🟩", "⬛"
MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

def xp_for_level(level: int) -> int: return XP_PER_LEVEL * level * level
def level_from_xp(xp: int) -> int: return math.isqrt(xp // XP_PER_LEVEL)
def progress_bar(current: int, needed: int, length: int = BAR_LENGTH) -> str:
    filled = round((current / needed) * length) if needed > 0 else length
    return BAR_FILLED * max(0, min(length, filled)) + BAR_EMPTY * (length - max(0, min(length, filled)))

class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cooldowns: dict[tuple[int, int], float] = {}

    @staticmethod
    async def _get_xp(guild_id: int, user_id: int) -> int:
        return await storage.get_user_xp(str(guild_id), str(user_id))

    @staticmethod
    async def _set_xp(guild_id: int, user_id: int, xp: int) -> None:
        await storage.set_user_xp(str(guild_id), str(user_id), xp)

    @staticmethod
    async def _get_guild_xp(guild_id: int) -> dict[int, int]:
        return await storage.get_guild_xp(str(guild_id))

    @staticmethod
    async def _get_role_rewards(guild_id: int) -> dict[int, int]:
        return await storage.get_role_rewards(str(guild_id))

    @staticmethod
    async def _set_role_rewards(guild_id: int, rewards: dict[int, int]) -> None:
        current = await storage.get_role_rewards(str(guild_id))
        for level, role_id in rewards.items():
            if current.get(level) != role_id:
                await storage.set_role_reward(str(guild_id), level, role_id)
        for level in current:
            if level not in rewards:
                await storage.remove_role_reward(str(guild_id), level)

    async def _grant_role_rewards(self, guild: discord.Guild, member: discord.Member, old_level: int, new_level: int) -> list[discord.Role]:
        rewards = await self._get_role_rewards(guild.id)
        if not rewards: return []
        to_grant = []
        for level in range(old_level + 1, new_level + 1):
            role_id = rewards.get(level)
            if not role_id: continue
            role = guild.get_role(role_id)
            if role and role not in member.roles: to_grant.append(role)
        if not to_grant: return []
        try:
            await member.add_roles(*to_grant, reason="Leveling: reached a role-reward level")
        except (discord.Forbidden, discord.HTTPException): return []
        return to_grant

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.author.bot: return
        key = (message.guild.id, message.author.id)
        now = time.time()
        if now - self._cooldowns.get(key, 0) < XP_COOLDOWN_SECONDS: return
        self._cooldowns[key] = now

        old_xp = await self._get_xp(message.guild.id, message.author.id)
        old_level = level_from_xp(old_xp)
        new_xp = old_xp + random.randint(XP_MIN, XP_MAX)
        new_level = level_from_xp(new_xp)
        await self._set_xp(message.guild.id, message.author.id, new_xp)

        if new_level > old_level:
            embed = discord.Embed(title="🎉 Level Up!", description=f"{message.author.mention} just reached **Level {new_level}**!", color=discord.Color.gold())
            embed.set_thumbnail(url=message.author.display_avatar.url)
            granted_roles = await self._grant_role_rewards(message.guild, message.author, old_level, new_level)
            if granted_roles:
                embed.add_field(name="🎖️ New role" + ("s" if len(granted_roles) > 1 else ""), value=", ".join(role.mention for role in granted_roles), inline=False)
            try: await message.channel.send(embed=embed)
            except discord.HTTPException: pass

    levelrole_group = app_commands.Group(name="levelrole", description="Configure which role is granted at which level", default_permissions=discord.Permissions(manage_guild=True), guild_only=True)

    @levelrole_group.command(name="set", description="Grant a role automatically at a level")
    async def levelrole_set(self, interaction: discord.Interaction, level: app_commands.Range[int, 1, MAX_REWARD_LEVEL], role: discord.Role):
        if role.is_default() or role.managed: return await interaction.response.send_message("❌ Invalid role.", ephemeral=True)
        if role >= interaction.guild.me.top_role: return await interaction.response.send_message("❌ I can't assign that role.", ephemeral=True)
        rewards = await self._get_role_rewards(interaction.guild.id)
        rewards[level] = role.id
        await self._set_role_rewards(interaction.guild.id, rewards)
        await interaction.response.send_message(f"✅ Members will now receive {role.mention} upon reaching **Level {level}**.")

    @levelrole_group.command(name="remove", description="Stop granting a role at a level")
    async def levelrole_remove(self, interaction: discord.Interaction, level: app_commands.Range[int, 1, MAX_REWARD_LEVEL]):
        rewards = await self._get_role_rewards(interaction.guild.id)
        if level not in rewards: return await interaction.response.send_message(f"❌ Level {level} doesn't have a role set.", ephemeral=True)
        del rewards[level]
        await self._set_role_rewards(interaction.guild.id, rewards)
        await interaction.response.send_message(f"🗑️ Removed the role reward for Level {level}.")

    @levelrole_group.command(name="list", description="Show every level-up role reward")
    async def levelrole_list(self, interaction: discord.Interaction):
        rewards = await self._get_role_rewards(interaction.guild.id)
        if not rewards: return await interaction.response.send_message("No level roles are configured yet.", ephemeral=True)
        lines = [f"**Level {level}** → {interaction.guild.get_role(rewards[level]).mention if interaction.guild.get_role(rewards[level]) else f'`deleted ({rewards[level]})`'}" for level in sorted(rewards)]
        embed = discord.Embed(title="🎖️ Level-Up Role Rewards", description="\n".join(lines), color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed)

    @levelrole_group.command(name="sync", description="Grant role rewards to members who already qualify")
    async def levelrole_sync(self, interaction: discord.Interaction):
        await interaction.response.defer()
        rewards = await self._get_role_rewards(interaction.guild.id)
        if not rewards: return await interaction.followup.send("No level roles configured.", ephemeral=True)
        guild_xp = await self._get_guild_xp(interaction.guild.id)
        updated, granted_total, failed = 0, 0, 0
        for member in interaction.guild.members:
            if member.bot: continue
            xp = guild_xp.get(member.id)
            if xp is None: continue
            level = level_from_xp(xp)
            to_grant = [interaction.guild.get_role(rid) for rl, rid in rewards.items() if rl <= level and (r := interaction.guild.get_role(rid)) and r not in member.roles]
            if not to_grant: continue
            try:
                await member.add_roles(*to_grant, reason="Leveling: /levelrole sync")
                updated += 1; granted_total += len(to_grant)
            except (discord.Forbidden, discord.HTTPException): failed += 1
        
        msg = f"✅ Updated {updated} member(s), granting {granted_total} role(s) total."
        if failed: msg += f"\n⚠️ Couldn't update {failed} member(s)."
        await interaction.followup.send(msg)

    @app_commands.command(name="rank", description="Show your (or someone else's) level and XP")
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        if interaction.guild is None: return await interaction.response.send_message("Only in servers.", ephemeral=True)
        member = member or interaction.user
        if member.bot: return await interaction.response.send_message("Bots don't earn XP.", ephemeral=True)
        
        guild_xp = await self._get_guild_xp(interaction.guild.id)
        xp = guild_xp.get(member.id, 0)
        level = level_from_xp(xp)
        floor_xp, next_floor = xp_for_level(level), xp_for_level(level + 1)
        rank_position = next((i + 1 for i, (uid, _) in enumerate(sorted(guild_xp.items(), key=lambda item: item[1], reverse=True)) if uid == member.id), None) if member.id in guild_xp else None
        
        embed = discord.Embed(title=f"📊 Rank — {member.display_name}", color=member.color if member.color.value else discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=str(level))
        embed.add_field(name="Total XP", value=f"{xp:,}")
        if rank_position: embed.add_field(name="Server Rank", value=f"#{rank_position}")
        embed.add_field(name="Progress to next level", value=f"{progress_bar(xp - floor_xp, next_floor - floor_xp)}\n`{xp - floor_xp:,} / {next_floor - floor_xp:,} XP`", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Show the server's top members by level")
    async def leaderboard(self, interaction: discord.Interaction):
        if interaction.guild is None: return await interaction.response.send_message("Only in servers.", ephemeral=True)
        guild_xp = await self._get_guild_xp(interaction.guild.id)
        if not guild_xp: return await interaction.response.send_message("Nobody has earned any XP yet.", ephemeral=True)
        
        lines, rank = [], 0
        for user_id, xp in sorted(guild_xp.items(), key=lambda item: item[1], reverse=True):
            member = interaction.guild.get_member(user_id)
            if not member: continue
            rank += 1
            if rank > 10: break
            lines.append(f"{MEDALS.get(rank, f'`#{rank}`')} {member.mention} — **Level {level_from_xp(xp)}** ({xp:,} XP)")
        
        if not lines: return await interaction.response.send_message("Nobody on the leaderboard is still in the server.", ephemeral=True)
        embed = discord.Embed(title=f"🏆 {interaction.guild.name} Leaderboard", description="\n".join(lines), color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))