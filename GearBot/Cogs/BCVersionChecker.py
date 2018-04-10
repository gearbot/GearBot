import asyncio

import aiohttp
from discord.ext import commands

from Util import GearbotLogging


class BCVersionChecker:

    def __init__(self, bot):
        self.bot:commands.Bot = bot
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
        self.running = False

    def loadVersions(self):
        pass



def setup(bot):
    bot.add_cog(BCVersionChecker(bot))

async def versionChecker(checkcog:BCVersionChecker):
    while not checkcog.bot.STARTUP_COMPLETE:
        await asyncio.sleep(1)
    GearbotLogging.info("Started BC version checking background task")
    session:aiohttp.ClientSession
    reply:aiohttp.ClientResponse
    while checkcog.running:
        async with aiohttp.ClientSession() as session:
            try:
                lastUpdate = 0
                async with session.get('https://www.mod-buildcraft.com/build_info_full/last_change.txt') as reply:
                    stamp = await reply.text()
                    if stamp > lastUpdate:
                        GearbotLogging.info("New BC version somewhere!")

                        lastUpdate = stamp
                    pass
            except Exception as ex:
                pass
    GearbotLogging.info("BC version checking background task terminated")


async def getList(session, url):
    async with session.get(url) as reply:
        return await reply.text().split("\n")[:-1]