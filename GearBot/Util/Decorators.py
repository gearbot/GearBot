from discord.ext import commands


def is_owner():
    async def predicate(ctx):
        return ctx.author.id == 106354106196570112
    return commands.check(predicate)