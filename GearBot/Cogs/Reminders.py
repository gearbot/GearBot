import asyncio
import time
from datetime import datetime

from discord import Embed, User, NotFound, Forbidden, DMChannel
from discord.ext import commands

from Bot import TheRealGearBot
from Cogs.BaseCog import BaseCog
from Util import Utils, GearbotLogging, Emoji, Translator, MessageUtils, server_info
from Util.Converters import Duration, ReminderText
from database.DatabaseConnector import Reminder, ReminderStatus


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
            one = Emoji.get_emoji("1")
            two = Emoji.get_emoji("2")
            no = Emoji.get_emoji("NO")
            embed = Embed(description=f"""
{Emoji.get_chat_emoji("1")} {Translator.translate("remind_option_here", ctx)}
{Emoji.get_chat_emoji("2")} {Translator.translate("remind_option_dm", ctx)}
{Emoji.get_chat_emoji("NO")} {Translator.translate("remind_option_cancel", ctx)}
""")
            m = await ctx.send(message, embed=embed)
            for e in [one, two, no]:
                await m.add_reaction(e)

            try:
                reaction, user = await ctx.bot.wait_for('reaction_add', timeout=30, check=lambda reaction,
                                                                                                 user: user == ctx.message.author and reaction.emoji in [one, two, no])
            except asyncio.TimeoutError:
                await MessageUtils.send_to(ctx, "NO", "confirmation_timeout", timeout=30)
                return
            else:
                if reaction.emoji == no:
                    await MessageUtils.send_to(ctx, "NO", "command_canceled")
                    return
                else:
                    dm = reaction.emoji == two
            finally:
                await m.delete()

        else:
            dm = True
        Reminder.create(user_id=ctx.author.id, channel_id=ctx.channel.id, dm=dm,
                        to_remind=await Utils.clean(reminder, markdown=False, links=False, emoji=False),
                        time=time.time() + duration_seconds, status=ReminderStatus.Pending,
                        guild_id=ctx.guild.id if ctx.guild is not None else "@me", message_id=ctx.message.id)
        mode = "dm" if dm else "here"
        await MessageUtils.send_to(ctx, "YES", f"reminder_confirmation_{mode}", duration=duration.length,
                                     duration_identifier=duration.unit)

    async def delivery_service(self):
        GearbotLogging.info("📬 Starting reminder delivery background task 📬")
        while self.running:
            now = datetime.fromtimestamp(time.time())
            limit = datetime.fromtimestamp(time.time() + 30)

            for r in Reminder.select().where(Reminder.time <= limit, Reminder.status == ReminderStatus.Pending):
                if r.id not in self.handling:
                    self.handling.add(r.id)
                    self.bot.loop.create_task(
                        self.run_after((r.time - now).total_seconds(), self.deliver(r)))
            await asyncio.sleep(10)
        GearbotLogging.info("📪 Reminder delivery background task terminated 📪")

    async def run_after(self, delay, action):
        if delay > 0:
            await asyncio.sleep(delay)
        if self.running:  # cog got terminated, new cog is now in charge of making sure this gets handled
            await action

    async def deliver(self, r):
        channel = self.bot.get_channel(r.channel_id)
        dm = self.bot.get_user(r.user_id)
        first = dm if r.dm else channel
        alternative = channel if r.dm else dm

        new_status = ReminderStatus.Delivered if (await self.attempt_delivery(first, r) or await self.attempt_delivery(alternative, r)) else ReminderStatus.Failed
        r.status = new_status
        r.save()

    async def attempt_delivery(self, location, package):
        try:
            if location is None:
                return False
            if package.guild_id is None:
                jumplink_available = "Unavailable"
            else:
                jumplink_available = MessageUtils.construct_jumplink(package.guild_id, package.channel_id, package.message_id)
            mode = "dm" if isinstance(location, User) else "channel"
            now = datetime.utcfromtimestamp(time.time())
            send_time = datetime.utcfromtimestamp(package.send.timestamp())
            parts = {
                "date": send_time.strftime('%c'),
                "timediff": server_info.time_difference(now, send_time, None if isinstance(location, User) or isinstance(location, DMChannel) else location.guild.id),
                "now_date": now.strftime('%c'),
                "jump_link": jumplink_available,
                "recipient": None if isinstance(location, User) else (await Utils.get_user(package.user_id)).mention
            }
            parcel = Translator.translate(f"reminder_delivery_{mode}", None if isinstance(location, User) or isinstance(location, DMChannel) else location, **parts)
            content = f"```\n{package.to_remind}\n```"
            try:
                if len(parcel) + len(content) < 2000:
                    await location.send(parcel + content)
                else:
                    await location.send(parcel)
                    await location.send(content)
            except (Forbidden, NotFound):
                return False
            else:
                return True
        except Exception as ex:
            await TheRealGearBot.handle_exception("Reminder delivery", self.bot, ex, None, None, None, location, package)
            return False


def setup(bot):
    bot.add_cog(Reminders(bot))
