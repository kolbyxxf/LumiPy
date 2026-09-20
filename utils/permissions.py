import discord


async def require_permission(
    interaction: discord.Interaction,
    permission: str
) -> bool:
    if not getattr(interaction.user.guild_permissions, permission):
        await interaction.response.send_message(
            "You don't have permission.", ephemeral=True
        )
        return False
    return True


def can_moderate(
    interaction: discord.Interaction,
    member: discord.Member
) -> bool:
    if member == interaction.user:
        return False
    if interaction.guild is None:
        return False
    if interaction.user.id == interaction.guild.owner_id:
        return True
    return member.top_role < interaction.user.top_role


async def reject_target(
    interaction: discord.Interaction,
    member: discord.Member
) -> bool:
    if not can_moderate(interaction, member):
        await interaction.response.send_message(
            "You can't moderate that member.", ephemeral=True
        )
        return True
    return False
