import contextlib
import io
import textwrap
import traceback
from datetime import datetime

import discord
from discord.ext import commands

from Bot.GearBot import GearBot
from Util import GearbotLogging, Utils, Configuration, Pages, Emoji
from Util.Converters import UserID


class Admin:

    def __init__(self, bot):
        self.bot:GearBot = bot
        Pages.register("eval", self.init_eval, self.update_eval, sender_only=True)

    def __unload(self):
        Pages.unregister("eval")

    async def __local_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)


    @commands.command(hidden=True)
    async def restart(self, ctx):
        """Restarts the bot"""
        await ctx.send("Restarting...")
        await Utils.cleanExit(self.bot, ctx.author.name)


    @commands.command(hidden=True)
    async def nuke_tasks(self, ctx):
        """nukes pending tasks"""
        for r in self.bot.running_events:
            r.cancel()

    @commands.command(hidden=True)
    async def upgrade(self, ctx):
        await ctx.send(f"{Emoji.get_chat_emoji('WRENCH')} I'll be right back with new gears! {Emoji.get_chat_emoji('WOOD')} {Emoji.get_chat_emoji('STONE')} {Emoji.get_chat_emoji('IRON')} {Emoji.get_chat_emoji('GOLD')} {Emoji.get_chat_emoji('DIAMOND')}")
        await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('REFRESH')} Upgrade initiated by {ctx.author.name}")
        GearbotLogging.info(f"Upgrade initiated by {ctx.author.name}")
        file = open("upgradeRequest", "w")
        file.write("upgrade requested")
        file.close()
        await self.bot.logout()
        await self.bot.close()

    @commands.command()
    async def stats(self, ctx):
        """Operational stats"""
        uptime = datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        days, hours = divmod(hours, 24)
        minutes, seconds = divmod(remainder, 60)
        tacos = "{:,}".format(round(self.bot.eaten))
        user_messages = "{:,}".format(self.bot.user_messages)
        bot_messages = "{:,}".format(self.bot.bot_messages)
        self_messages = "{:,}".format(self.bot.self_messages)
        await ctx.send(
            f"<:gearDiamond:433284297345073153> Gears have been spinning for {days} {'day' if days is 1 else 'days'}, {hours} {'hour' if hours is 1 else 'hours'}, {minutes} {'minute' if minutes is 1 else 'minutes'} and {seconds} {'second' if seconds is 1 else 'seconds'}\n"
            f"<:gearGold:433284297554788352> I received {user_messages} user messages and {bot_messages} bot messages ({self_messages} were my own) so far\n"
            f"<:gearIron:433284297563045901> Number of times ks has grinded my gears (causing errors): {self.bot.errors}\n"
            f"<:gearStone:433284297340878849> {self.bot.commandCount} commands have been executed, as well as {self.bot.custom_command_count} custom commands\n"
            f"<:gearWood:433284297336815616> Working in {len(self.bot.guilds)} guilds\n"
            f":taco: About {tacos} tacos could have been produced and eaten in this time\n"
            f"<:todo:433693576036352024> Add more stats")

    @commands.command()
    async def reconnectdb(self, ctx):
        """Disconnect and reconnect the database, for case it does run away again"""
        self.bot.database_connection.close()
        self.bot.database_connection.connect()
        await ctx.send("Database connection re-established")



    @commands.command()
    async def setstatus(self, ctx, type:int, *, status:str):
        """Sets a playing/streaming/listening/watching status"""
        await self.bot.change_presence(activity=discord.Activity(name=status, type=type))
        await ctx.send("Status updated")

    @commands.command()
    async def reloadconfigs(self, ctx:commands.Context):
        """Reloads all server configs from disk"""
        async with ctx.typing():
            Configuration.load_master()
            await Configuration.initialize(self.bot)
        await ctx.send("Configs reloaded")

    @commands.command(hidden=True)
    async def eval(self, ctx:commands.Context, *, code: str):
        output = None
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message
        }

        env.update(globals())

        if code.startswith('```'):
            code = "\n".join(code.split("\n")[1:-1])

        out = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(code, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            output = f'{e.__class__.__name__}: {e}'
        else:
            func = env['func']
            try:
                with contextlib.redirect_stdout(out):
                    ret = await func()
            except Exception as e:
                value = out.getvalue()
                output = f'{value}{traceback.format_exc()}'
            else:
                value = out.getvalue()
                if ret is None:
                    if value:
                        output = value
                else:
                    output = f'{value}{ret}'
        if output is not None:
            await Pages.create_new("eval", ctx, pages=Pages.paginate(output))
        else:
            await ctx.message.add_reaction(Emoji.emojis["YES"])

    async def init_eval(self, ctx, pages):
        page = pages[0]
        num = len(pages)
        return f"**Eval output 1/{num}**\n```py\n{page}```", None, num > 1, []

    async def update_eval(self, ctx, message, page_num, action, data):
        pages = data["pages"]
        page, page_num = Pages.basic_pages(pages, page_num, action)
        return f"**Eval output {page_num + 1}/{len(pages)}**\n```py\n{page}```", None, page_num


    @commands.command(hidden=True)
    async def post_info(self, ctx, name):
        with open(f"{name}.txt", "r") as file:
            pages = Pages.paginate("".join(file.readlines()), 500, 2000)
            await ctx.channel.purge(limit=len(pages) + 2)
            await ctx.send(file=discord.File(f"{name}.png"))
            for page in pages:
                await ctx.send(page)

    @commands.command()
    async def set_presence(self, ctx, name):
        await self.bot.change_presence(status=name, activity=ctx.me.activity)

    @commands.command()
    async def mutuals(self, ctx, user:UserID):
        mutuals = []
        for guild in self.bot.guilds:
            if guild.get_member(user) is not None:
                mutuals.append(guild)
        for page in Pages.paginate("\n".join(f"{guild.id} - {guild.name}" for guild in mutuals), prefix="```py\n", suffix="```"):
            await ctx.send(page)



def setup(bot):
    bot.add_cog(Admin(bot))
