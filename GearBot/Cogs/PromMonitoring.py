import asyncio

from aiohttp import web

import discord
from discord.ext import commands

import prometheus_client as prom
from prometheus_client.exposition import generate_latest

from Cogs.PromMetrics import PromMetrics
from Cogs.BaseCog import BaseCog


class PromMonitoring(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.running = True
        
        self.metrics = PromMetrics()

        self.bot.loop.create_task(self.raw_stats_updater())

        self.metric_server = self.bot.loop.create_task(self.create_site())

    def cog_unload(self):
        self.running = False
        self.metric_server.cancel()


    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        self.metrics.command_counter.labels(
            command_name = ctx.invoked_with,
            guild_id = ctx.guild.id
        ).inc()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        self.metrics.guild_messages.labels(
            guild_id = message.guild.id
        ).inc()

        self.metrics.messages_to_length.labels(
            length = len(message.content)
        )

    async def raw_stats_updater(self):
        while self.running:
            old_count = int(self.metrics.bot_message_raw_count.collect()[0].samples[0].value)
            new_count = self.bot.bot_messages
            if new_count != old_count:
                inc_value = (new_count - old_count) # Keep the dashboards stats up to date with the internal count
                self.metrics.bot_message_raw_count.inc(inc_value)

            old_count = int(self.metrics.user_message_raw_count.collect()[0].samples[0].value)
            new_count = self.bot.user_messages
            if new_count != old_count:
                inc_value = (new_count - old_count)
                self.metrics.user_message_raw_count.inc(inc_value)
            
            if not self.running: return

            await asyncio.sleep(10)


    async def create_site(self):
        metrics_app = web.Application()
        metrics_app.add_routes([web.get("/", serve_metrics)])

        runner = web.AppRunner(metrics_app)
        await self.bot.loop.create_task(runner.setup())
        site = web.TCPSite(runner)
        await site.start()

        return site

    async def serve_metrics(self, request):
        metrics_to_server = generate_latest(self.metrics.metrics_reg).decode("utf-8")
        print("Here: " + metrics_to_server)
        return web.Response(text=metrics_to_server, content_type="text/plain")


def setup(bot):
    bot.add_cog(PromMonitoring(bot))