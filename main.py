import os
import discord
from discord.ext import commands

# Your specific Server ID
GUILD_ID = 1551112474487554148
TOKEN = os.environ["DCTOKEN"]

COGS = [
    "cogs.general",
    "cogs.afk",
    "cogs.moderation",
    "cogs.welcome_goodbye",
    "cogs.autoroles",
    "cogs.reaction_roles",
    "cogs.dropdown_roles",
    "cogs.cleanup",
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True


class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 1. Load all cogs
        for cog in COGS:
            await self.load_extension(cog)
            print(f"Loaded cog: {cog}")
        
        total_commands = len(self.tree.get_commands())
        print(f"Total commands found in tree: {total_commands}")

        # 2. DEBUG: Check if the bot is actually in the target guild
        # Note: get_guild might return None if the bot hasn't fully connected yet,
        # but usually works by the time setup_hook finishes.
        target_guild = self.get_guild(GUILD_ID)
        if target_guild:
            print(f"✅ Bot IS in server: {target_guild.name}")
        else:
            print(f"❌ Bot is NOT in server ID {GUILD_ID}. It is in:")
            for g in self.guilds:
                print(f"   - {g.name} (ID: {g.id})")

        # 3. Sync GLOBALLY (This will make commands appear in ALL servers)
        try:
            synced = await self.tree.sync() 
            print(f"Successfully synced {len(synced)} GLOBAL commands.")
        except discord.HTTPException as error:
            print(f"Sync failed: {error}")

    async def on_ready(self):
        print(f"{self.user} is running fine!")


client = Client()

if __name__ == "__main__":
    client.run(TOKEN)
