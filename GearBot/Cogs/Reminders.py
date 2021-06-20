import asyncio
import time
from datetime import datetime

from discord import Embed, User, NotFound, Forbidden, DMChannel, MessageReference
from discord.ext import commands

from Bot import TheRealGearBot
from Cogs.BaseCog import BaseCog
from Util import Utils, GearbotLogging, Emoji, Translator, MessageUtils, server_info
from Util.Converters import Duration, ReminderText
from Util.Utils import assemble_jumplink
from database.DatabaseConnector import Reminder


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

    @commands.bot_has_permissions(add_reactions=True)
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
                reaction = await ctx.bot.wait_for('raw_reaction_add', timeout=30, check=lambda reaction: reaction.user_id == ctx.message.author.id and reaction.emoji in [one, two, no])
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
        await Reminder.create(user_id=ctx.author.id, channel_id=ctx.channel.id, dm=dm,
                        to_remind=await Utils.clean(reminder, markdown=False, links=False, emoji=False),
                        time=time.time() + duration_seconds, send=datetime.now().timestamp(), status=1,
                        guild_id=ctx.guild.id if ctx.guild is not None else "@me", message_id=ctx.message.id)
        mode = "dm" if dm else "here"
        await MessageUtils.send_to(ctx, "YES", f"reminder_confirmation_{mode}", duration=duration.length,
                                     duration_identifier=duration.unit)

    async def delivery_service(self):
        # only let cluster 0 do this one
        if self.bot.cluster != 0:
            return
        GearbotLogging.info("📬 Starting reminder delivery background task 📬")
        while self.running:
            now = time.time()
            limit = datetime.fromtimestamp(time.time() + 30).timestamp()

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
            now = datetime.utcfromtimestamp(time.time())
            send_time = datetime.utcfromtimestamp(package.send)
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
