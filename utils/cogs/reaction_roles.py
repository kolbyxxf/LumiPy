import discord
from discord import app_commands
from discord.ext import commands

from utils import storage
from utils.permissions import require_permission


class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reaction_roles: dict = storage.load_reaction_roles()

    @app_commands.command(name="reactionrole", description="Create a reaction role")
    async def reactionrole(
        self,
        interaction: discord.Interaction,
        channel_id: str,
        message_id: str,
        emoji: str,
        role_id: str,
    ):
        if not await require_permission(interaction, "manage_guild"):
            return
        if not channel_id.isdigit() or not message_id.isdigit() or not role_id.isdigit():
            await interaction.response.send_message(
                "The IDs must be numbers only.", ephemeral=True
            )
            return
        channel = interaction.guild.get_channel(int(channel_id))
        if channel is None:
            await interaction.response.send_message(
                "I can't find that channel.", ephemeral=True
            )
            return
        role = interaction.guild.get_role(int(role_id))
        if role is None:
            await interaction.response.send_message(
                "I can't find that role.", ephemeral=True
            )
            return
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "My role must be above that role.", ephemeral=True
            )
            return
        try:
            message = await channel.fetch_message(int(message_id))
            await message.add_reaction(emoji)
        except discord.NotFound:
            await interaction.response.send_message(
                "I can't find that message.", ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "I couldn't add that reaction.", ephemeral=True
            )
            return

        message_key = str(message.id)
        if message_key not in self.reaction_roles:
            self.reaction_roles[message_key] = {
                "guild_id": interaction.guild.id,
                "channel_id": channel.id,
                "roles": {},
            }
        self.reaction_roles[message_key]["roles"][emoji] = role.id
        storage.save_reaction_roles(self.reaction_roles)
        await interaction.response.send_message(
            f"{emoji} now gives {role.mention}.", ephemeral=True
        )

    @app_commands.command(name="removereactionrole", description="Remove a reaction role")
    async def removereactionrole(
        self,
        interaction: discord.Interaction,
        message_id: str,
        emoji: str,
    ):
        if not await require_permission(interaction, "manage_guild"):
            return
        if not message_id.isdigit():
            await interaction.response.send_message(
                "The message ID must be a number.", ephemeral=True
            )
            return
        config = self.reaction_roles.get(message_id)
        if config is None:
            await interaction.response.send_message(
                "That message has no reaction roles.", ephemeral=True
            )
            return
        if emoji not in config["roles"]:
            await interaction.response.send_message(
                "That emoji has no reaction role.", ephemeral=True
            )
            return
        role_id = config["roles"].pop(emoji)
        if config["roles"]:
            self.reaction_roles[message_id] = config
        else:
            self.reaction_roles.pop(message_id)
        storage.save_reaction_roles(self.reaction_roles)

        channel = interaction.guild.get_channel(int(config["channel_id"]))
        if channel:
            try:
                message = await channel.fetch_message(int(message_id))
                await message.clear_reaction(emoji)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        role = interaction.guild.get_role(int(role_id))
        role_name = role.mention if role else f"`{role_id}`"
        await interaction.response.send_message(
            f"{emoji} no longer gives {role_name}.", ephemeral=True
        )

    @app_commands.command(
        name="clearreactionroles",
        description="Remove all reaction roles from a message",
    )
    async def clearreactionroles(self, interaction: discord.Interaction, message_id: str):
        if not await require_permission(interaction, "manage_guild"):
            return
        if not message_id.isdigit():
            await interaction.response.send_message(
                "The message ID must be a number.", ephemeral=True
            )
            return
        config = self.reaction_roles.get(message_id)
        if config is None:
            await interaction.response.send_message(
                "That message has no reaction roles.", ephemeral=True
            )
            return
        channel = interaction.guild.get_channel(int(config["channel_id"]))
        if channel:
            try:
                message = await channel.fetch_message(int(message_id))
                for emoji in config["roles"]:
                    await message.clear_reaction(emoji)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
        self.reaction_roles.pop(message_id)
        storage.save_reaction_roles(self.reaction_roles)
        await interaction.response.send_message(
            "All reaction roles have been removed from that message.",
            ephemeral=True,
        )

    async def _resolve(self, payload: discord.RawReactionActionEvent):
        config = self.reaction_roles.get(str(payload.message_id))
        if config is None:
            return None
        role_id = config["roles"].get(str(payload.emoji))
        if role_id is None:
            return None
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return None
        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.NotFound:
                return None
        role = guild.get_role(int(role_id))
        if role is None or role >= guild.me.top_role:
            return None
        return member, role

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        resolved = await self._resolve(payload)
        if resolved is None:
            return
        member, role = resolved
        try:
            await member.add_roles(role, reason="Reaction role")
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        resolved = await self._resolve(payload)
        if resolved is None:
            return
        member, role = resolved
        try:
            await member.remove_roles(role, reason="Reaction role removed")
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRoles(bot))
