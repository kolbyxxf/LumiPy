import discord
from discord import app_commands
from discord.ext import commands
from utils.storage import load_data, save_data

class AutoRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data_file = "autorole.json"

    @app_commands.command(name="setautorole", description="Set roles to be automatically assigned to new members")
    @app_commands.default_permissions(administrator=True)
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        data = load_data(self.data_file)
        guild_id = str(interaction.guild.id)
        
        if guild_id not in data:
            data[guild_id] = []
            
        if role.id not in data[guild_id]:
            data[guild_id].append(role.id)
            save_data(self.data_file, data)
            await interaction.response.send_message(f"✅ Role **{role.name}** added to auto-roles.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ That role is already in the auto-role list.", ephemeral=True)

    @app_commands.command(name="removeautorole", description="Remove a role from auto-assignment")
    @app_commands.default_permissions(administrator=True)
    async def remove_autorole(self, interaction: discord.Interaction, role: discord.Role):
        data = load_data(self.data_file)
        guild_id = str(interaction.guild.id)
        
        if guild_id in data and role.id in data[guild_id]:
            data[guild_id].remove(role.id)
            save_data(self.data_file, data)
            await interaction.response.send_message(f"✅ Role **{role.name}** removed from auto-roles.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ That role is not in the auto-role list.", ephemeral=True)

    @app_commands.command(name="viewautoroles", description="View current auto-roles")
    async def view_autoroles(self, interaction: discord.Interaction):
        data = load_data(self.data_file)
        guild_id = str(interaction.guild.id)
        
        if guild_id not in data or not data[guild_id]:
            await interaction.response.send_message("No auto-roles configured.", ephemeral=True)
            return
            
        roles = []
        for role_id in data[guild_id]:
            role = interaction.guild.get_role(role_id)
            if role:
                roles.append(role.mention)
            else:
                data[guild_id].remove(role_id)
                save_data(self.data_file, data)
                
        await interaction.response.send_message(f"Auto-roles: {' '.join(roles) if roles else 'None'}", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = load_data(self.data_file)
        guild_id = str(member.guild.id)
        
        if guild_id in data:
            for role_id in data[guild_id]:
                role = member.guild.get_role(role_id)
                if role:
                    try:
                        await member.add_roles(role, reason="AutoRole System")
                    except discord.Forbidden:
                        pass

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRoles(bot))
