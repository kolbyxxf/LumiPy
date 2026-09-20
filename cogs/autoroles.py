import discord
from discord import app_commands
from discord.ext import commands

from utils import storage
from utils.permissions import require_permission


class AutoRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.autoroles: dict = storage.load_autorole()

    @app_commands.command(name="setautorole", description="Add a role to automatic roles")
    async def setautorole(self, interaction: discord.Interaction, role_id: str):
        if not await require_permission(interaction, "manage_guild"):
            return
        if not role_id.isdigit():
            await interaction.response.send_message(
                "The role ID must be a number.", ephemeral=True
            )
            return
        role = interaction.guild.get_role(int(role_id))
        if role is None:
            await interaction.response.send_message(
                "I can't find that role.", ephemeral=True
            )
            return
        guild_id = str(interaction.guild.id)
        if guild_id not in self.autoroles:
            self.autoroles[guild_id] = []
        if role.id in self.autoroles[guild_id]:
            await interaction.response.send_message(
                "That role is already an auto-role.", ephemeral=True
            )
            return
        self.autoroles[guild_id].append(role.id)
        storage.save_autorole(self.autoroles)
        await interaction.response.send_message(
            f"{role.mention} added as an auto-role.", ephemeral=True
        )

    @app_commands.command(name="removeautorole", description="Remove a role from automatic roles")
    async def removeautorole(self, interaction: discord.Interaction, role_id: str):
        if not await require_permission(interaction, "manage_guild"):
            return
        if not role_id.isdigit():
            await interaction.response.send_message(
                "The role ID must be a number.", ephemeral=True
            )
            return
        guild_id = str(interaction.guild.id)
        role_list = self.autoroles.get(guild_id, [])
        role_id = int(role_id)
        if role_id not in role_list:
            await interaction.response.send_message(
                "That role isn't an auto-role.", ephemeral=True
            )
            return
        role_list.remove(role_id)
        if role_list:
            self.autoroles[guild_id] = role_list
        else:
            self.autoroles.pop(guild_id)
        storage.save_autorole(self.autoroles)
        role = interaction.guild.get_role(role_id)
        role_name = role.mention if role else f"`{role_id}`"
        await interaction.response.send_message(
            f"{role_name} removed from auto-roles.", ephemeral=True
        )

    @app_commands.command(name="clearautoroles", description="Remove all automatic roles")
    async def clearautoroles(self, interaction: discord.Interaction):
        if not await require_permission(interaction, "manage_guild"):
            return
        guild_id = str(interaction.guild.id)
        if guild_id not in self.autoroles:
            await interaction.response.send_message(
                "There are no auto-roles configured.", ephemeral=True
            )
            return
        self.autoroles.pop(guild_id)
        storage.save_autorole(self.autoroles)
        await interaction.response.send_message(
            "All auto-roles have been removed.", ephemeral=True
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        for role_id in self.autoroles.get(str(member.guild.id), []):
            role = member.guild.get_role(int(role_id))
            if role is None:
                continue
            if role >= member.guild.me.top_role:
                continue
            try:
                await member.add_roles(role, reason="Automatic role")
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRoles(bot))
