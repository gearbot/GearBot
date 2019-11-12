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
            command_name = ctx.command.qualified_name,
        ).inc()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        m = self.bot.metrics

        m.guild_messages.labels(
            guild_id = message.guild.id if message.guild is not None else 0
        ).inc()


        (m.own_message_raw_count if message.author.id == self.bot.user.id else m.bot_message_raw_count if message.author.bot else m.user_message_raw_count).inc()

    async def create_site(self):
        await asyncio.sleep(15)
        metrics_app = web.Application()
        metrics_app.add_routes([web.get("/metrics", self.serve_metrics)])

        runner = web.AppRunner(metrics_app)
        await self.bot.loop.create_task(runner.setup())
        site = web.TCPSite(runner)
        await site.start()

        self.metric_server = site

    async def serve_metrics(self, request):
        metrics_to_server = generate_latest(self.bot.metrics_reg).decode("utf-8")
        return web.Response(text=metrics_to_server, content_type="text/plain")


def setup(bot):
    bot.add_cog(PromMonitoring(bot))
