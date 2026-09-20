import datetime
import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils import storage
from utils.permissions import require_permission


def parse_duration(value: str) -> int | None:
    value = value.lower().strip()
    if len(value) < 2:
        return None
    try:
        amount = int(value[:-1])
    except ValueError:
        return None
    if amount <= 0:
        return None
    unit = value[-1]
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    multiplier = multipliers.get(unit)
    if multiplier is None:
        return None
    return amount * multiplier


class Cleanup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cleanup_settings: dict = storage.load_cleanup()

    async def cog_load(self):
        self.cleanup_loop.start()

    async def cog_unload(self):
        self.cleanup_loop.cancel()

    @tasks.loop(minutes=1)
    async def cleanup_loop(self):
        now = discord.utils.utcnow()
        for channel_id, config in self.cleanup_settings.items():
            if not config.get("enabled"):
                continue
            guild = self.bot.get_guild(int(config["guild_id"]))
            if guild is None:
                continue
            channel = guild.get_channel(int(channel_id))
            if not isinstance(channel, discord.TextChannel):
                continue
            mode = config.get("mode")
            if mode == "age":
                cutoff = now - datetime.timedelta(seconds=config["age_seconds"])
                try:
                    await channel.purge(limit=None, before=cutoff)
                except discord.Forbidden:
                    continue
            elif mode == "schedule":
                scheduled_at = datetime.datetime.fromisoformat(config["scheduled_at"])
                if now >= scheduled_at:
                    try:
                        await channel.purge(limit=None)
                    except discord.Forbidden:
                        continue
                    config["enabled"] = False
                    storage.save_cleanup(self.cleanup_settings)

    @cleanup_loop.before_loop
    async def before_cleanup_loop(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="cleanup_age", description="Delete messages older than a duration"
    )
    async def cleanup_age(
        self,
        interaction: discord.Interaction,
        channel_id: str,
        age: str,
    ):
        if not await require_permission(interaction, "manage_messages"):
            return
        if not channel_id.isdigit():
            await interaction.response.send_message(
                "The channel ID must be a number.", ephemeral=True
            )
            return
        seconds = parse_duration(age)
        if seconds is None:
            await interaction.response.send_message(
                "Use a duration like `30m`, `2h`, `7d` or `1w`.", ephemeral=True
            )
            return
        channel = interaction.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "That isn't a text channel.", ephemeral=True
            )
            return
        self.cleanup_settings[str(channel.id)] = {
            "guild_id": interaction.guild.id,
            "channel_id": channel.id,
            "mode": "age",
            "age_seconds": seconds,
            "scheduled_at": None,
            "enabled": True,
        }
        storage.save_cleanup(self.cleanup_settings)
        await interaction.response.send_message(
            f"Messages older than `{age}` will now be automatically deleted "
            f"in {channel.mention}.",
            ephemeral=True,
        )

    @app_commands.command(name="cleanup_schedule", description="Schedule a channel cleanup")
    async def cleanup_schedule(
        self,
        interaction: discord.Interaction,
        channel_id: str,
        date_time: str,
    ):
        if not await require_permission(interaction, "manage_messages"):
            return
        if not channel_id.isdigit():
            await interaction.response.send_message(
                "The channel ID must be a number.", ephemeral=True
            )
            return
        channel = interaction.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "That isn't a text channel.", ephemeral=True
            )
            return
        try:
            scheduled_at = datetime.datetime.strptime(
                date_time, "%Y-%m-%d %H:%M"
            ).replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            await interaction.response.send_message(
                "Use `YYYY-MM-DD HH:MM` in UTC.", ephemeral=True
            )
            return
        if scheduled_at <= discord.utils.utcnow():
            await interaction.response.send_message(
                "That time has already passed.", ephemeral=True
            )
            return
        self.cleanup_settings[str(channel.id)] = {
            "guild_id": interaction.guild.id,
            "channel_id": channel.id,
            "mode": "schedule",
            "age_seconds": None,
            "scheduled_at": scheduled_at.isoformat(),
            "enabled": True,
        }
        storage.save_cleanup(self.cleanup_settings)
        await interaction.response.send_message(
            f"{channel.mention} will be cleaned at `{date_time} UTC`.",
            ephemeral=True,
        )

    @app_commands.command(
        name="cleanup_toggle", description="Enable or disable channel cleanup"
    )
    async def cleanup_toggle(
        self,
        interaction: discord.Interaction,
        channel_id: str,
        enabled: bool,
    ):
        if not await require_permission(interaction, "manage_messages"):
            return
        if not channel_id.isdigit():
            await interaction.response.send_message(
                "The channel ID must be a number.", ephemeral=True
            )
            return
        config = self.cleanup_settings.get(channel_id)
        if config is None:
            await interaction.response.send_message(
                "That channel has no cleanup configuration.", ephemeral=True
            )
            return
        config["enabled"] = enabled
        storage.save_cleanup(self.cleanup_settings)
        state = "enabled" if enabled else "disabled"
        await interaction.response.send_message(
            f"Cleanup {state} for <#{channel_id}>.", ephemeral=True
        )

    @app_commands.command(
        name="clearcleanup", description="Remove cleanup configuration"
    )
    async def clearcleanup(self, interaction: discord.Interaction, channel_id: str):
        if not await require_permission(interaction, "manage_messages"):
            return
        if not channel_id.isdigit():
            await interaction.response.send_message(
                "The channel ID must be a number.", ephemeral=True
            )
            return
        if channel_id not in self.cleanup_settings:
            await interaction.response.send_message(
                "That channel has no cleanup configuration.", ephemeral=True
            )
            return
        self.cleanup_settings.pop(channel_id)
        storage.save_cleanup(self.cleanup_settings)
        await interaction.response.send_message(
            f"Cleanup configuration removed from <#{channel_id}>.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Cleanup(bot))
