from discord.ext import commands
from discord.ext.commands import NoPrivateMessage, BotMissingPermissions, CheckFailure

from Util import Configuration


def is_owner():
    async def predicate(ctx):
        return ctx.bot.is_owner(ctx.author)

    return commands.check(predicate)


def is_trusted(member):
    return is_user("TRUSTED", member)


def is_mod(member):
    return is_user("MOD", member) or (hasattr(member, "roles") and member.guild_permissions.ban_members)


def is_admin(member):
    return is_user("ADMIN", member) or (hasattr(member, "roles") and member.guild_permissions.administrator)


def is_lvl4(member):
    return is_user("LVL4", member)


def is_server_owner(ctx):
    return ctx.guild is not None and ctx.author == ctx.guild.owner


def is_user(perm_type, member):
    if not hasattr(member, "guild") or member.guild is None:
        return False
    if not hasattr(member, "roles"):
        return False

    roles = Configuration.get_var(member.guild.id, "PERMISSIONS", f"{perm_type}_ROLES")
    users = Configuration.get_var(member.guild.id, "PERMISSIONS", f"{perm_type}_USERS")

    if member.id in users:
        return True

    for role in member.roles:
        if role.id in roles:
            return True
    return False


def mod_only():
    async def predicate(ctx):
        return is_mod(ctx.author) or is_admin(ctx.author)

    return commands.check(predicate)


def is_server(ctx, id):
    return ctx.guild is not None and ctx.guild.id == id


def bc_only():
    async def predicate(ctx):
        return is_server(ctx, 309218657798455298)

    return commands.check(predicate)

class NotCachedException(CheckFailure):
    pass


def require_cache():
    async def predicate(ctx):
        if ctx.guild is not None and ctx.guild.id in ctx.bot.missing_guilds:
            raise NotCachedException
        return True
    return commands.check(predicate)

def check_permission(command_object, guild, member):
    if guild is None:
        return 0 >= get_required(command_object, command_object.cog.permissions)
    else:
        overrides = Configuration.get_var(guild.id, "PERM_OVERRIDES")
        cog_name = type(command_object.cog).__name__
        required = -1
        if cog_name in overrides:
            required = get_required(command_object, overrides[cog_name])
        if required == -1:
            required = get_required(command_object, command_object.cog.permissions)
        return get_user_lvl(guild, member, command_object) >= (command_object.cog.permissions["required"] if required == -1 else required)


def get_command_pieces(command_object):
    return command_object.qualified_name.lower().split(" ") if command_object is not None else []


def get_required(command_object, perm_dict):
    return get_perm_dict(get_command_pieces(command_object), perm_dict)["required"]


def get_perm_dict(pieces, perm_dict, strict=False):
    found = True
    while len(pieces) > 0 and found:
        found = False
        if "commands" in perm_dict.keys():
            for entry, value in perm_dict["commands"].items():
                if pieces[0] in entry.split("|"):
                    perm_dict = value
                    pieces.pop(0)
                    found = True
                    break
            if not found and len(pieces) > 0 and strict:
                return None
    return perm_dict


def get_user_lvl(guild, member, command_object=None):
    if guild.owner is not None and guild.owner.id == member.id:
        return 5

    if is_lvl4(member):
        return 4

    if command_object is not None:
        cog_name = type(command_object.cog).__name__
        overrides = Configuration.get_var(guild.id, "PERM_OVERRIDES")
        if cog_name in overrides:
            target = overrides[cog_name]
            pieces = get_command_pieces(command_object)
            while len(pieces) > 0 and "commands" in target and pieces[0] in target["commands"]:
                target = target["commands"][pieces.pop(0)]
                if member.id in target["people"]:
                    return 4
    if is_admin(member):
        return 3
    if is_mod(member):
        return 2
    if is_trusted(member):
        return 1
    return 0


def user_lvl(member):
    if member.guild.owner.id == member.id:
        return 5
    if is_lvl4(member):
        return 4
    if is_admin(member):
        return 3
    if is_mod(member):
        return 2
    if is_trusted(member):
        return 1
    return 0


def bot_has_guild_permission(**kwargs):
    async def predicate(ctx):
        if ctx.guild is None:
            raise NoPrivateMessage()

        permissions = ctx.guild.me.guild_permissions
        missing = [perm for perm, value in kwargs.items() if getattr(permissions, perm, None) != value]

        if not missing:
            return True

        raise BotMissingPermissions(missing)

    return commands.check(predicate)

