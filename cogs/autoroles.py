import discord
from discord import app_commands
from discord.ext import commands
from utils import storage

class AutoRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setautorole", description="Set roles to be automatically assigned to new members")
    @app_commands.default_permissions(administrator=True)
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        guild_id = str(interaction.guild.id)
        roles = await storage.get_autoroles(guild_id)
        if role.id in roles:
            return await interaction.response.send_message("⚠️ That role is already in the auto-role list.", ephemeral=True)
        await storage.add_autorole(guild_id, role.id)
        await interaction.response.send_message(f"✅ Role **{role.name}** added to auto-roles.", ephemeral=True)

    @app_commands.command(name="removeautorole", description="Remove a role from auto-assignment")
    @app_commands.default_permissions(administrator=True)
    async def remove_autorole(self, interaction: discord.Interaction, role: discord.Role):
        guild_id = str(interaction.guild.id)
        roles = await storage.get_autoroles(guild_id)
        if role.id not in roles:
            return await interaction.response.send_message("❌ That role is not in the auto-role list.", ephemeral=True)
        await storage.remove_autorole(guild_id, role.id)
        await interaction.response.send_message(f"✅ Role **{role.name}** removed from auto-roles.", ephemeral=True)

    @app_commands.command(name="viewautoroles", description="View current auto-roles")
    async def view_autoroles(self, interaction: discord.Interaction):
        roles_ids = await storage.get_autoroles(str(interaction.guild.id))
        if not roles_ids:
            return await interaction.response.send_message("No auto-roles configured.", ephemeral=True)
        
        mentions = []
        for role_id in roles_ids:
            role = interaction.guild.get_role(role_id)
            if role: mentions.append(role.mention)
        await interaction.response.send_message(f"Auto-roles: {' '.join(mentions) if mentions else 'None'}", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        roles_ids = await storage.get_autoroles(str(member.guild.id))
        for role_id in roles_ids:
            role = member.guild.get_role(role_id)
            if role:
                try: await member.add_roles(role, reason="AutoRole System")
                except discord.Forbidden: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRoles(bot))