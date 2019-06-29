from discord.ext import commands

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


def check_permission(ctx: commands.Context):
    if ctx.guild is None:
        return 0 >= get_required(ctx, ctx.cog.permissions)
    else:
        overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
        cog_name = type(ctx.cog).__name__
        required = -1
        if cog_name in overrides:
            required = get_required(ctx, overrides[cog_name])
        if required == -1:
            required = get_required(ctx, ctx.cog.permissions)
        return get_user_lvl(ctx) >= (ctx.cog.permissions["required"] if required == -1 else required)


def get_command_pieces(ctx):
    parts = (ctx.message.content[len(ctx.prefix):] if ctx.prefix is not None else ctx.message.content).split(" ")
    command_object = None
    while len(parts) > 0 and command_object is None:
        command_object = ctx.bot.get_command(" ".join(parts))
        parts.pop(len(parts) - 1)
    return command_object.qualified_name.lower().split(" ") if command_object is not None else []


def get_required(ctx, perm_dict):
    return get_perm_dict(get_command_pieces(ctx), perm_dict)["required"]


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


def get_user_lvl(ctx: commands.Context):
    if is_server_owner(ctx):
        return 5

    if is_lvl4(ctx.author):
        return 4

    cog_name = type(ctx.cog).__name__
    overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
    if cog_name in overrides:
        target = overrides[cog_name]
        pieces = get_command_pieces(ctx)
        while len(pieces) > 0 and "commands" in target and pieces[0] in target["commands"]:
            target = target["commands"][pieces.pop(0)]
            if ctx.author.id in target["people"]:
                return 4
    if is_admin(ctx.author):
        return 3
    if is_mod(ctx.author):
        return 2
    if is_trusted(ctx.author):
        return 1
    return 0


def user_lvl(member):
    if member.guild.owner == member:
        return 5
    if is_lvl4(member):
        return 4
    if is_admin(member):
        return 3
    if is_mod(member):
        return 2
    if is_trusted(member):
        return 1
