import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta

class Cleanup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="cleanup_age", description="Remove roles from members older than X days")
    @app_commands.default_permissions(administrator=True)
    async def cleanup_age(self, interaction: discord.Interaction, role: discord.Role, days: int):
        await interaction.response.defer(ephemeral=True)
        
        cutoff_date = discord.utils.utcnow() - timedelta(days=days)
        removed_count = 0
        
        for member in role.members:
            if member.joined_at and member.joined_at < cutoff_date:
                try:
                    await member.remove_roles(role, reason=f"Cleanup: Older than {days} days")
                    removed_count += 1
                except discord.Forbidden:
                    continue
                    
        await interaction.followup.send(f"✅ Removed **{role.name}** from {removed_count} members.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Cleanup(bot))
