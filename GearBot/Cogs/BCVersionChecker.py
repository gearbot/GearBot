import asyncio


class BCVersionChecker:

    def __init__(self, bot):
        self.bot = bot
        self.BC_VERSION_LIST = {}
        self.BCC_VERSION_LIST = {}
        self.BCT_VERSION_LIST = {}
        self.BCCT_VERSION_LIST = {}
        self.LAST_UPDATE = 0
        self.ALLOWED_TO_ANNOUNCE = True
        self.VERSIONS_PER_MC_VERSION = {}
        self.running = True
        self.loadVersions()
        self.bot.loop.create_task(versionChecker(self))

    def __unload(self):
        #cleanup
        pass



def setup(bot):
    bot.add_cog(BCVersionChecker(bot))

async def versionChecker(checkcog:BCVersionChecker):
    while not checkcog.bot.STARTUP_COMPLETE:
        await asyncio.sleep(1)