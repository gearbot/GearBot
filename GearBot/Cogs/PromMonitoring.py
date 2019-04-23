import asyncio

import discord
import prometheus_client as prom
from discord.ext import commands

from Cogs.BaseCog import BaseCog


class PromMonitoring(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.running = True
        self.command_counter = prom.Counter("commands_ran", "How many times commands were ran and who ran them", [
            "command_name",
            "author_name",
            "author_id",
            "guild_id"
        ])

        self.message_counter = prom.Counter("messages_sent", "What messages have been sent and by who", [
            "author_name",
            "author_id",
            "guild_id",
            "length"
        ])

        self.user_message_raw_count = prom.Counter("user_message_raw_count", "Raw count of how many messages we have seen from users")
        self.bot_message_raw_count = prom.Counter("bot_message_raw_count", "Raw count of how many messages we have seen from bots")
        
        self.bot.loop.create_task(self.raw_stats_updater())

        self.metric_server = prom.start_http_server(8082)

    def cog_unload(self):
        self.running = False


    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        self.command_counter.labels(
            command_name = ctx.invoked_with,
            author_name = ctx.author,
            author_id = ctx.author.id,
            guild_id = ctx.guild.id
        ).inc()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return
        self.message_counter.labels(
            author_name = message.author,
            author_id = message.author.id,
            guild_id = message.guild.id,
            length = len(message.content)
        ).inc()


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


def setup(bot):
    bot.add_cog(PromMonitoring(bot))