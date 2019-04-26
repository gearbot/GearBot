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
        self.bot.loop.create_task(self.raw_stats_updater())

        self.bot.loop.create_task(self.create_site())

    def cog_unload(self):
        self.running = False
        self.bot.loop.create_task(self.metric_server.stop())


    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        self.bot.metrics.command_counter.labels(
            command_name = ctx.invoked_with,
            guild_id = ctx.guild.id
        ).inc()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        self.bot.metrics.guild_messages.labels(
            guild_id = message.guild.id
        ).inc()

        self.bot.metrics.messages_to_length.labels(
            length = len(message.content)
        )

    async def raw_stats_updater(self):
        while self.running:
            metrics = self.bot.metrics
            old_count = int(self.bot.metrics.bot_message_raw_count.collect()[0].samples[0].value)
            new_count = self.bot.bot_messages
            if new_count != old_count:
                inc_value = (new_count - old_count) # Keep the dashboards stats up to date with the internal count
                self.bot.metrics.bot_message_raw_count.inc(inc_value)

            old_count = int(self.bot.metrics.user_message_raw_count.collect()[0].samples[0].value)
            new_count = self.bot.user_messages
            if new_count != old_count:
                inc_value = (new_count - old_count)
                self.bot.metrics.user_message_raw_count.inc(inc_value)
            
            if not self.running: return

            await asyncio.sleep(10)

    async def create_site(self):
        await asyncio.sleep(5)
        metrics_app = web.Application()
        metrics_app.add_routes([web.get("/metrics", self.serve_metrics)])

        runner = web.AppRunner(metrics_app)
        await self.bot.loop.create_task(runner.setup())
        site = web.TCPSite(runner)
        await site.start()

        self.metric_server = site

    async def serve_metrics(self, request):
        metrics_to_server = generate_latest(self.bot.metrics_reg).decode("utf-8")
        print("Here: " + metrics_to_server)
        return web.Response(text=metrics_to_server, content_type="text/plain")


def setup(bot):
    bot.add_cog(PromMonitoring(bot))
