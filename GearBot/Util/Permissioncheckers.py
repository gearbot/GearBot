from discord.ext import commands

from Util import Configuration


def is_owner():
    async def predicate(ctx):
        return ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)


def isServerAdmin(ctx:commands.Context):
    if ctx.guild is None:
        return False
    adminrole = Configuration.getConfigVar(ctx.guild.id, "ADMIN_ROLE_ID")
    if adminrole != 0:
        for role in ctx.author.roles:
            if str(role.id) == str(adminrole):
                return True
    return ctx.author == ctx.guild.owner


def isServerMod(ctx:commands.Context):
    if ctx.guild is None:
        return False
    modrole = Configuration.getConfigVar(ctx.guild.id, "MOD_ROLE_ID")
    if modrole != 0:
        for role in ctx.author.roles:
            if str(role.id) == str(modrole):
                return True
    return isServerAdmin(ctx)

def modOnly():
    async def predicate(ctx):
        return isServerMod(ctx)
    return commands.check(predicate)

def isDev(ctx:commands.Context):
    if ctx.guild is None:
        return False
    devrole = Configuration.getConfigVar(ctx.guild.id, "DEV_ROLE")
    if devrole != 0:
        for role in ctx.author.roles:
            if role.id == devrole:
                return True
    return isServerAdmin(ctx)

def devOnly():
    async def predicate(ctx):
        return isDev(ctx)
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