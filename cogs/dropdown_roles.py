import discord
from discord import app_commands
from discord.ext import commands
from utils import storage
from utils.permissions import require_permission

class RoleSelect(discord.ui.Select):
    def __init__(self, cog: "DropdownRoles", message_id: int, roles: list[dict]):
        options = [discord.SelectOption(label=role["label"], value=str(role["role"]), emoji=role.get("emoji")) for role in roles]
        super().__init__(placeholder="Select your roles...", min_values=0, max_values=len(options), options=options, custom_id=f"role_select:{message_id}")
        self.cog = cog
        self.message_id = message_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.guild is None: return
        config = self.cog.dropdown_roles.get(str(self.message_id))
        if config is None: return await interaction.response.send_message("This role menu no longer exists.", ephemeral=True)
        
        selected = {int(role_id) for role_id in self.values}
        available = {int(role["role"]) for role in config["roles"]}
        member = interaction.user
        
        for role_id in available:
            role = interaction.guild.get_role(role_id)
            if role is None: continue
            if role_id in selected:
                if role not in member.roles:
                    try: await member.add_roles(role, reason="Dropdown role")
                    except discord.Forbidden: pass
            elif role in member.roles:
                try: await member.remove_roles(role, reason="Dropdown role")
                except discord.Forbidden: pass
        await interaction.response.send_message("Your roles have been updated.", ephemeral=True)

class RoleSelectView(discord.ui.View):
    def __init__(self, cog: "DropdownRoles", message_id: int, roles: list[dict]):
        super().__init__(timeout=None)
        self.add_item(RoleSelect(cog, message_id, roles))

class DropdownRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dropdown_roles: dict = {}

    async def cog_load(self):
        self.dropdown_roles = await storage.load_dropdown_roles()
        for message_id, config in self.dropdown_roles.items():
            try:
                self.bot.add_view(RoleSelectView(self, int(message_id), config["roles"]), message_id=int(message_id))
            except (ValueError, KeyError): pass

    @app_commands.command(name="dropdownrole", description="Create a dropdown role menu")
    async def dropdownrole(self, interaction: discord.Interaction, title: str, roles: str):
        if not await require_permission(interaction, "manage_guild"): return
        entries = [entry.strip() for entry in roles.split(",") if entry.strip()]
        if not entries: return await interaction.response.send_message("Add at least one role.", ephemeral=True)
        if len(entries) > 25: return await interaction.response.send_message("A dropdown can contain at most 25 roles.", ephemeral=True)

        role_data = []
        for entry in entries:
            parts = entry.split("|")
            if len(parts) < 2: return await interaction.response.send_message("Use: `ROLE_ID|Label|Emoji`", ephemeral=True)
            role_id, label = parts[0].strip(), parts[1].strip()
            emoji = parts[2].strip() if len(parts) >= 3 else None
            if not role_id.isdigit(): return await interaction.response.send_message(f"Invalid role ID: `{role_id}`", ephemeral=True)
            role = interaction.guild.get_role(int(role_id))
            if role is None: return await interaction.response.send_message(f"I can't find role `{role_id}`.", ephemeral=True)
            if role >= interaction.guild.me.top_role: return await interaction.response.send_message(f"I can't manage {role.mention}.", ephemeral=True)
            role_data.append({"role": role.id, "label": label[:100], "emoji": emoji})

        embed = discord.Embed(title=title, description="Select your roles below.", color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        
        msg_id_str = str(message.id)
        info = {"guild_id": interaction.guild.id, "channel_id": interaction.channel.id, "roles": role_data}
        self.dropdown_roles[msg_id_str] = info
        await storage.set_dropdown_role(msg_id_str, interaction.guild.id, interaction.channel.id, role_data)
        await message.edit(view=RoleSelectView(self, message.id, role_data))

    @app_commands.command(name="removedropdownrole", description="Remove a dropdown role menu")
    async def removedropdownrole(self, interaction: discord.Interaction, message_id: str):
        if not await require_permission(interaction, "manage_guild"): return
        if not message_id.isdigit(): return await interaction.response.send_message("The message ID must be a number.", ephemeral=True)
        
        config = self.dropdown_roles.get(message_id)
        if config is None: return await interaction.response.send_message("That dropdown role menu doesn't exist.", ephemeral=True)
        
        self.dropdown_roles.pop(message_id)
        await storage.remove_dropdown_role(message_id)
        
        channel = interaction.guild.get_channel(int(config["channel_id"]))
        if channel:
            try:
                message = await channel.fetch_message(int(message_id))
                await message.edit(view=None)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException): pass
        await interaction.response.send_message("The dropdown role menu has been removed.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(DropdownRoles(bot))