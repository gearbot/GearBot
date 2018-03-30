from discord.ext import commands

from Util import Configuration


def is_owner():
    async def predicate(ctx):
        return ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)


def isServerAdmin(ctx:commands.Context):
    adminrole = Configuration.getConfigVar(ctx.guild.id, "ADMIN_ROLE_ID")
    if adminrole != 0:
        for role in ctx.author.roles:
            if str(role.id) == str(adminrole):
                return True
    return ctx.author == ctx.guild.owner


def isServerMod(ctx:commands.Context):
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