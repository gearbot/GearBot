from Cogs.Bot import bot


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
    async def ping(self, ctx):
        await ctx.send("pong")

def setup(bot):
    bot.add_cog(Basic(bot))