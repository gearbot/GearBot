import asyncio

import discord
from aiohttp import web
from discord.ext import commands
from prometheus_client.exposition import generate_latest

from Cogs.BaseCog import BaseCog


class PromMonitoring(BaseCog):


    def __init__(self, bot):
        super().__init__(bot)
        self.running = True
        self.bot.loop.create_task(self.create_site())

    def cog_unload(self):
        self.running = False
        self.bot.loop.create_task(self.metric_server.stop())


    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        self.bot.metrics.command_counter.labels(
            cluster=self.bot.cluster,
            command_name= ctx.command.qualified_name,
        ).inc()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        m = self.bot.metrics


        (m.own_message_raw_count if message.author.id == self.bot.user.id else m.bot_message_raw_count if message.author.bot else m.user_message_raw_count).labels(cluster=self.bot.cluster).inc()

    async def create_site(self):
        await asyncio.sleep(15)
        metrics_app = web.Application()
        metrics_app.add_routes([web.get("/metrics", self.serve_metrics)])

        runner = web.AppRunner(metrics_app)
        await self.bot.loop.create_task(runner.setup())
        site = web.TCPSite(runner, host='0.0.0.0', port=8090)

        await site.start()

        self.metric_server = site

    async def serve_metrics(self, request):
        self.bot.metrics.bot_users.labels(cluster=self.bot.cluster).set(sum(len(g.members) for g in self.bot.guilds))
        self.bot.metrics.bot_users_unique.labels(cluster=self.bot.cluster).set(len(self.bot.users))
        self.bot.metrics.bot_guilds.labels(cluster=self.bot.cluster).set(len(self.bot.guilds))
        self.bot.metrics.bot_latency.labels(cluster=self.bot.cluster).set((self.bot.latency))

        metrics_to_server = generate_latest(self.bot.metrics_reg).decode("utf-8")
        return web.Response(text=metrics_to_server, content_type="text/plain")


def setup(bot):
    bot.add_cog(PromMonitoring(bot))
