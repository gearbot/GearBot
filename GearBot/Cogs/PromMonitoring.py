import asyncio

from aiohttp import web

import discord
from discord.ext import commands

import prometheus_client as prom
from prometheus_client.exposition import generate_latest

from Cogs.BaseCog import BaseCog


class PromMonitoring(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.running = True
        self.command_counter = prom.Counter("commands_ran", "How many times commands were ran and who ran them", [
            "command_name",
            "guild_id"
        ])

        self.guild_messages = prom.Counter("messages_sent", "What messages have been sent and by who", [
            "guild_id"
        ])

        self.messages_to_length = prom.Counter("messages_to_length", "Keeps track of what messages were what length", [
            "length"
        ])

        self.user_message_raw_count = prom.Counter("user_message_raw_count", "Raw count of how many messages we have seen from users")
        self.bot_message_raw_count = prom.Counter("bot_message_raw_count", "Raw count of how many messages we have seen from bots")
        
        self.bot.loop.create_task(self.raw_stats_updater())

        self.metric_server = self.bot.loop.create_task(self.create_site())

    def cog_unload(self):
        self.running = False
        self.metric_server.cancel()


    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        self.command_counter.labels(
            command_name = ctx.invoked_with,
            guild_id = ctx.guild.id
        ).inc()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return

        self.guild_messages.labels(
            guild_id = message.guild.id
        ).inc()

        self.messages_to_length.labels(
            length = len(message.content)
        )

    async def raw_stats_updater(self):
        while self.running:
            old_count = int(self.bot_message_raw_count.collect()[0].samples[0].value)
            new_count = self.bot.bot_messages
            if new_count != old_count:
                inc_value = (new_count - old_count) # Keep the dashboards stats up to date with the internal count
                self.bot_message_raw_count.inc(inc_value)

            old_count = int(self.user_message_raw_count.collect()[0].samples[0].value)
            new_count = self.bot.user_messages
            if new_count != old_count:
                inc_value = (new_count - old_count)
                self.user_message_raw_count.inc(inc_value)
            
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

async def serve_metrics(request):
    metrics_to_server = generate_latest().decode("utf-8")
    return web.Response(text=metrics_to_server, content_type="text/plain")


def setup(bot):
    bot.add_cog(PromMonitoring(bot))