from Cogs.Bot import bot


class Admin:

    def __init__(self, bot):
        self.bot = bot

    def __unload(self):
        print('cleanup goes here')

    def __global_check(self, ctx):
        return True

    def __global_check_once(self, ctx):
        return True

    async def __local_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)

    async def __error(self, ctx, error):
        print('Error in {0.command.qualified_name}: {1}'.format(ctx, error))

    async def __before_invoke(self, ctx):
        print('cog local before: {0.command.qualified_name}'.format(ctx))

    async def __after_invoke(self, ctx):
        print('cog local after: {0.command.qualified_name}'.format(ctx))

    @bot.command()
    async def test(self, ctx, arg):
        await ctx.send(arg)

def setup(bot):
    bot.add_cog(Admin(bot))