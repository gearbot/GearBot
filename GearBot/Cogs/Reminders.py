import asyncio
import time
import datetime

from discord import Embed, User, NotFound, Forbidden, DMChannel, MessageReference
from discord.ext import commands

from Bot import TheRealGearBot
from Cogs.BaseCog import BaseCog
from Util import Utils, GearbotLogging, Emoji, Translator, MessageUtils, server_info
from Util.Converters import Duration, ReminderText
from Util.Utils import assemble_jumplink
from database.DatabaseConnector import Reminder
from views.Reminder import ReminderView


class Reminders(BaseCog):

    def __init__(self, bot) -> None:
        super().__init__(bot)

        self.running = True
        self.handling = set()
        self.bot.loop.create_task(self.delivery_service())

    def cog_unload(self):
        self.running = False

    @commands.group(aliases=["r", "reminder"])
    async def remind(self, ctx):
        """remind_help"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.bot.get_command("help"), query="remind")

    @remind.command("me", aliases=["add", "m", "a"])
    async def remind_me(self, ctx, duration: Duration, *, reminder: ReminderText):
        """remind_me_help"""
        if duration.unit is None:
            parts = reminder.split(" ")
            duration.unit = parts[0]
            reminder = " ".join(parts[1:])
        duration_seconds = duration.to_seconds(ctx)
        if duration_seconds <= 0:
            await MessageUtils.send_to(ctx, "NO", "reminder_time_travel")
            return
        if ctx.guild is not None:
            message = f'{Emoji.get_chat_emoji("QUESTION")} {Translator.translate("remind_question", ctx)}'

            async def timeout():
                if m is not None:
                    await m.edit(content=MessageUtils.assemble(ctx, 'NO', 'command_canceled'), view=None)

            m = await ctx.send(message, view=ReminderView(guild_id=ctx.guild.id if ctx.guild is not None else "@me", reminder=reminder, channel_id=ctx.channel.id, user_id=ctx.author.id, message_id=ctx.message.id, duration=duration_seconds, timeout_callback=timeout))


    async def delivery_service(self):
        # only let cluster 0 do this one
        if self.bot.cluster != 0:
            return
        GearbotLogging.info("📬 Starting reminder delivery background task 📬")
        while self.running:
            now = time.time()
            limit = datetime.datetime.fromtimestamp(time.time() + 30).timestamp()

            for r in await Reminder.filter(time__lt = limit, status = 1):
                if r.id not in self.handling:
                    self.handling.add(r.id)
                    self.bot.loop.create_task(
                        self.run_after(r.time - now, self.deliver(r)))
            await asyncio.sleep(25)
        GearbotLogging.info("📪 Reminder delivery background task terminated 📪")

    async def run_after(self, delay, action):
        if delay > 0:
            await asyncio.sleep(delay)
        if self.running:  # cog got terminated, new cog is now in charge of making sure this gets handled
            await action

    async def deliver(self, r):
        channel = None
        try:
            channel = await self.bot.fetch_channel(r.channel_id)
        except (Forbidden, NotFound):
            pass
        dm = await self.bot.fetch_user(r.user_id)
        first = dm if r.dm else channel
        alternative = channel if r.dm else dm

        if not await self.attempt_delivery(first, r):
            await self.attempt_delivery(alternative, r)
        await r.delete()

    async def attempt_delivery(self, location, package):
        try:
            if location is None:
                return False



            tloc =  None if isinstance(location, User) or isinstance(location, DMChannel) else location
            now = datetime.datetime.fromtimestamp(time.time())
            send_time = datetime.datetime.fromtimestamp(package.send)
            desc = Translator.translate('reminder_delivery', tloc, date=send_time.strftime('%c'), timediff=server_info.time_difference(now, send_time, tloc)) + f"```\n{package.to_remind}\n```"
            desc = Utils.trim_message(desc, 2048)
            embed = Embed(
                color=16698189,
                title=Translator.translate('reminder_delivery_title', tloc),
                description=desc
            )
            if location.id == package.channel_id or package.guild_id == '@me':
                ref = MessageReference(guild_id=package.guild_id if package.guild_id != '@me' else None, channel_id=package.channel_id, message_id=package.message_id, fail_if_not_exists=False)
            else:
                ref = None
                embed.add_field(name=Translator.translate('jump_link', tloc), value=f'[Click me!]({assemble_jumplink(package.guild_id, package.channel_id, package.message_id)})')

            try:
                await location.send(embed=embed, reference=ref)
            except (Forbidden, NotFound):
                return False
            else:
                return True
        except Exception as ex:
            await TheRealGearBot.handle_exception("Reminder delivery", self.bot, ex, None, None, None, location, package)
            return False


def setup(bot):
    bot.add_cog(Reminders(bot))
