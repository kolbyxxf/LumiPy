import logging
import logging.handlers
import os
import sys
import time
import traceback
import discord
from discord.ext import commands

GUILD_ID = 1551112474487554148
INITIAL_RESTART_DELAY = 5
MAX_RESTART_DELAY = 300
MIN_UPTIME_TO_RESET = 60

try:
    TOKEN = os.environ["DCTOKEN"]
except KeyError:
    print("❌ DCTOKEN environment variable is not set. Set it and try again.")
    sys.exit(1)

COGS = [
    "cogs.general", "cogs.afk", "cogs.moderation", "cogs.welcome_goodbye",
    "cogs.autoroles", "cogs.reaction_roles", "cogs.dropdown_roles",
    "cogs.cleanup", "cogs.ticket", "cogs.automod", "cogs.security", "cogs.leveling",
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

def setup_logging() -> logging.Logger:
    logger = logging.getLogger("bot")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    file_handler = None
    try:
        file_handler = logging.handlers.RotatingFileHandler(filename="bot.log", encoding="utf-8", maxBytes=5 * 1024 * 1024, backupCount=3)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.warning("Could not open bot.log for writing: %s", exc)
        
    discord_logger = logging.getLogger("discord")
    discord_logger.setLevel(logging.WARNING)
    discord_logger.addHandler(console_handler)
    if file_handler: discord_logger.addHandler(file_handler)
    return logger

log = setup_logging()

class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 1. Initialize DB and run migration BEFORE loading cogs
        from utils import storage, migration
        await storage.init_db()
        await migration.run_migration()
        
        # 2. Load Cogs
        await self._load_cogs()
        self._log_command_count()
        self._check_target_guild()
        await self._sync_commands()

    async def _load_cogs(self):
        loaded, failed = 0, []
        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info("Loaded cog: %s", cog)
                loaded += 1
            except commands.ExtensionAlreadyLoaded:
                log.warning("Cog already loaded, skipping: %s", cog)
            except commands.ExtensionNotFound:
                log.error("Cog not found: %s", cog)
                failed.append(cog)
            except commands.NoEntryPointError:
                log.error("Cog has no setup() function: %s", cog)
                failed.append(cog)
            except commands.ExtensionFailed as exc:
                log.error("Cog %s failed to load:\n%s", cog, "".join(traceback.format_exception(exc.original)))
                failed.append(cog)
            except Exception:
                log.exception("Unexpected error loading cog: %s", cog)
                failed.append(cog)
        log.info("Cog loading finished: %d loaded, %d failed.", loaded, len(failed))
        if failed:
            log.warning("Bot is starting without: %s", ", ".join(failed))

    def _log_command_count(self):
        log.info("Total commands found in tree: %d", len(self.tree.get_commands()))

    def _check_target_guild(self):
        target_guild = self.get_guild(GUILD_ID)
        if target_guild:
            log.info("Bot IS in target server: %s", target_guild.name)
        else:
            log.warning("Bot is NOT in target server ID %s.", GUILD_ID)
            if self.guilds:
                for g in self.guilds: log.info("  In server: %s (ID: %s)", g.name, g.id)
            else:
                log.warning("Bot is not in any servers yet.")

    async def _sync_commands(self):
        try:
            synced = await self.tree.sync()
            log.info("Successfully synced %d global commands.", len(synced))
        except discord.HTTPException:
            log.exception("Slash command sync failed")
        except discord.Forbidden:
            log.exception("Missing permissions to sync slash commands")

    async def on_ready(self):
        log.info("%s is running fine! (ID: %s)", self.user, self.user.id)

    async def on_error(self, event_method, *args, **kwargs):
        log.error("Unhandled exception in event %s", event_method, exc_info=sys.exc_info())

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound): return
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to do that."); return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument: `{error.param.name}`."); return
        log.error("Unhandled command error in !%s", getattr(ctx.command, "qualified_name", "?"), exc_info=error)
        await ctx.send("⚠️ Something went wrong running that command.")

    async def on_disconnect(self):
        log.warning("Bot disconnected from Discord (will try to reconnect).")

    async def on_resumed(self):
        log.info("Bot session resumed.")

def build_client() -> Client:
    client = Client()
    @client.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            message = f"⏳ That command is on cooldown. Try again in {error.retry_after:.1f}s."
        elif isinstance(error, discord.app_commands.MissingPermissions):
            message = "❌ You don't have permission to do that."
        elif isinstance(error, discord.app_commands.BotMissingPermissions):
            message = "❌ I don't have the permissions needed to do that."
        else:
            log.error("Unhandled app command error in /%s", getattr(interaction.command, "name", "?"), exc_info=error)
            message = "⚠️ Something went wrong running that command."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            log.exception("Failed to send app command error message to user")
    return client

def run_forever():
    delay = INITIAL_RESTART_DELAY
    while True:
        client = build_client()
        started_at = time.monotonic()
        try:
            client.run(TOKEN, log_handler=None)
            log.info("Bot shut down cleanly. Not restarting.")
            return
        except discord.LoginFailure:
            log.critical("Login failed: DCTOKEN is invalid or has been reset. Not restarting.")
            return
        except KeyboardInterrupt:
            log.info("Shutting down (Ctrl+C).")
            return
        except Exception:
            log.critical("Bot crashed unexpectedly.", exc_info=True)
            if time.monotonic() - started_at >= MIN_UPTIME_TO_RESET:
                delay = INITIAL_RESTART_DELAY
            log.warning("Restarting in %d seconds...", delay)
            time.sleep(delay)
            delay = min(delay * 2, MAX_RESTART_DELAY)

if __name__ == "__main__":
    run_forever()