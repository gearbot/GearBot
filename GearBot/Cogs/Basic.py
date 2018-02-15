import time

from discord.ext import commands

from Bot import bot
from Util import Decorators

class Basic:

    def __init__(self, bot):
        self.bot = bot

    def __unload(self):
        #cleanup
        pass

    def __global_check(self, ctx):
        return True

    def __global_check_once(self, ctx):
        return True

    async def __local_check(self, ctx):
        return True

    async def __error(self, ctx, error):
        print('Error in {0.command.qualified_name}: {1}'.format(ctx, error))

    async def __before_invoke(self, ctx):
        print('cog local before: {0.command.qualified_name}'.format(ctx))

    async def __after_invoke(self, ctx):
        print('cog local after: {0.command.qualified_name}'.format(ctx))

    @bot.command()
    async def ping(self, ctx:commands.Context):
        if (Decorators.is_owner()(ctx)):
            t1 = time.perf_counter()
            await ctx.trigger_typing()
            t2 = time.perf_counter()
            await ctx.send(f":hourglass: Gateway ping is {round((t2 - t1) * 1000)}ms :hourglass:")
        else:
            await ctx.send("pong")

def setup(bot):
    bot.add_cog(Basic(bot))