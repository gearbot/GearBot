from discord.ext import commands

from Util import Configuration


def is_owner():
    async def predicate(ctx):
        return ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)


def is_trusted(ctx):
    return is_user("TRUSTED", ctx)

def is_mod(ctx:commands.Context):
    return is_user("MOD", ctx) or (hasattr(ctx.author, "roles") and ctx.channel.permissions_for(ctx.author).ban_members)

def is_admin(ctx:commands.Context):
    return is_user("ADMIN", ctx) or (hasattr(ctx.author, "roles") and ctx.channel.permissions_for(ctx.author).administrator)

def is_server_owner(ctx):
    return ctx.guild is not None and ctx.author == ctx.guild.owner


def is_user(perm_type, ctx):
    if ctx.guild is None:
        return False
    if not hasattr(ctx.author, "roles"):
        return False
    roles = Configuration.get_var(ctx.guild.id, f"{perm_type}_ROLES")
    for role in ctx.author.roles:
        if role.id in roles:
            return True
    return False

def mod_only():
    async def predicate(ctx):
        return is_mod(ctx) or is_admin(ctx)
    return commands.check(predicate)

def is_dev(ctx:commands.Context):
    if ctx.guild is None:
        return False
    devrole = Configuration.get_var(ctx.guild.id, "DEV_ROLE")
    if devrole != 0:
        for role in ctx.author.roles:
            if role.id == devrole:
                return True
    return is_admin(ctx)

def devOnly():
    async def predicate(ctx):
        return is_dev(ctx)
    return commands.check(predicate)

def is_server(ctx, id):
    return ctx.guild is not None and ctx.guild.id == id

def bc_only():
    async def predicate(ctx):
        return is_server(ctx, 309218657798455298)
    return commands.check(predicate)

def no_testers():
    async def predicate(ctx):
        return not is_server(ctx, 197038439483310086)
    return commands.check(predicate)

def check_permission(ctx:commands.Context):
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
        parts.pop(len(parts)-1)
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

def get_user_lvl(ctx:commands.Context):
    if is_server_owner(ctx):
        return 5
    cog_name = type(ctx.cog).__name__
    overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
    if cog_name in overrides:
        target = overrides[cog_name]
        pieces = get_command_pieces(ctx)
        while len(pieces) > 0 and "commands" in target and pieces[0] in target["commands"]:
            target = target["commands"][pieces.pop(0)]
            if ctx.author.id in target["people"]:
                return 4
    if is_admin(ctx):
        return 3
    if is_mod(ctx):
        return 2
    if is_trusted(ctx):
        return 1
    return 0