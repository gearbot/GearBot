import asyncio

import aiohttp

from Cogs.BaseCog import BaseCog
from Util import GearbotLogging, Configuration


class Cachet(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.session = aiohttp.ClientSession(loop=bot.loop)
        self.heartbeat_task = self.bot.loop.create_task(self.hearbeating())
        self.restping_task = self.bot.loop.create_task(self.restping_latency())

    def cog_unload(self):
        self.heartbeat_task.cancel()
        self.restping_task.cancel()
        GearbotLogging.info("Cachet tasks terminated!")

    async def hearbeating(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(60)
            json = {"value": f"{self.bot.latency * 1000}"}
            async with self.session.post(f"{self.cachet_url}/1/points", headers=self.headers, json=json) as r:
                pass


    async def restping_latency(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(60)
            m = await self.cachet_channel.send('1')
            await m.edit(content="2", delete_after=3.0)
            diff = m.edited_at - m.created_at
            json = {"value": diff.total_seconds() * 1000}
            async with self.session.post(f"{self.cachet_url}/2/points", headers=self.headers, json=json) as r:
                pass

    @property
    def headers(self):
        return {"X-Cachet-Token": Configuration.get_master_var("CACHET")["TOKEN"]}

    @property
    def cachet_channel(self):
        return self.bot.get_channel(Configuration.get_master_var("CACHET")["CHANNEL"])

    @property
    def cachet_url(self):
        return Configuration.get_master_var("CACHET")["URL"]

def setup(bot):
    bot.add_cog(Cachet(bot))