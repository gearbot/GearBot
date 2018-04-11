import asyncio

import aiohttp
from discord.ext import commands

from Util import GearbotLogging


class BCVersionChecker:

    def __init__(self, bot):
        self.bot:commands.Bot = bot
        self.BC_VERSION_LIST = {}
        self.BCC_VERSION_LIST = {}
        self.ALLOWED_TO_ANNOUNCE = True
        self.running = True
        self.force = False
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
    lastUpdate = 0
    async with aiohttp.ClientSession() as session:
        while checkcog.running:
            try:
                async with session.get('https://www.mod-buildcraft.com/build_info_full/last_change.txt') as reply:
                    stamp = await reply.text()
                    stamp = int(stamp[:-1])
                    if stamp > lastUpdate:
                        GearbotLogging.info("New BC version somewhere!")
                        lastUpdate = stamp
                    pass
            except Exception as ex:
                pass
            for i in range(1,60):
                if checkcog.force:
                    break
                await asyncio.sleep(10)

    GearbotLogging.info("BC version checking background task terminated")


async def getList(session, link):
    async with session.get(f"https://www.mod-buildcraft.com/build_info_full/{link}/versions.json") as reply:
        return await reply.json()