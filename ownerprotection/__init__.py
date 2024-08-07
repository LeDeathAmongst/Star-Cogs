from redbot.core.bot import Red
from .ownerprotection import (
    OwnerProtection,
    add_to_protected_owners,
    remove_from_protected_owners,
    create_support_role,
    delete_support_role,
    toggle_admin_permissions,
    list_protected_owners,
)

async def setup(bot: Red):
    cog = OwnerProtection(bot)
    await cog.cog_load()
    bot.add_cog(cog)
    bot.tree.add_command(add_to_protected_owners)
    bot.tree.add_command(remove_from_protected_owners)

async def teardown(bot: Red):
    bot.tree.remove_command("Add to Protected Owners", type=discord.AppCommandType.user)
    bot.tree.remove_command("Remove from Protected Owners", type=discord.AppCommandType.user)
