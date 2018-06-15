import asyncio
import contextlib
import io
import os
import subprocess
import textwrap
import traceback
from datetime import datetime
from subprocess import Popen

import discord
from discord.ext import commands

from Util import GearbotLogging, Utils, Configuration


class Admin:

    def __init__(self, bot):
        self.bot:commands.Bot = bot

    async def __local_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)


    @commands.command(hidden=True)
    async def restart(self, ctx):
        """Restarts the bot"""
        await ctx.send("Restarting...")
        await Utils.cleanExit(self.bot, ctx.author.name)

    @commands.command(hidden=True)
    async def upgrade(self, ctx):
        await ctx.send("<:BCWrench:344163417981976578> I'll be right back with new gears! <:woodGear:344163118089240596> <:stoneGear:344163146325295105> <:ironGear:344163170664841216> <:goldGear:344163202684289024> <:diamondGear:344163228101640192>")
        await GearbotLogging.logToBotlog(f"Upgrade initiated by {ctx.author.name}", log=True)
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
        tacos, remainder = divmod(int(uptime.total_seconds()), 15)
        await ctx.send(
            f"<:gearDiamond:433284297345073153> Gears have been spinning for {days} {'day' if days is 1 else 'days'}, {hours} {'hour' if hours is 1 else 'hours'}, {minutes} {'minute' if minutes is 1 else 'minutes'} and {seconds} {'second' if seconds is 1 else 'seconds'}\n"
            f"<:gearGold:433284297554788352> {self.bot.messageCount} messages have been processed\n"
            f"<:gearIron:433284297563045901> Number of times ks has grinded my gears (causing errors): {self.bot.errors}\n"
            f"<:gearStone:433284297340878849> Numbers of command executed: {self.bot.commandCount}\n"
            f"<:gearWood:433284297336815616> Working in {len(self.bot.guilds)} guilds\n"
            f":taco: About {tacos} tacos could have been produced and eaten in this time\n"
            f"<:todo:433693576036352024> Add more stats")

    @commands.command()
    async def reconnectdb(self, ctx):
        """Disconnect and reconnect the database, for in case it does run away again"""
        self.bot.database_connection.close()
        self.bot.database_connection.connect()
        await ctx.send("Database connection re-established")

    @commands.command()
    async def pull(self, ctx):
        """Pulls from github so an upgrade can be performed without full restart"""
        async with ctx.typing():
            p = Popen(["git pull origin master"], cwd=os.getcwd(), shell=True, stdout=subprocess.PIPE)
            while p.poll() is None:
                await asyncio.sleep(1)
            out, error = p.communicate()
            await ctx.send(f"Pull completed with exit code {p.returncode}```yaml\n{out.decode('utf-8')}```")

    @commands.command()
    async def setstatus(self, ctx, type:int, *, status:str):
        await self.bot.change_presence(activity=discord.Activity(name=status, type=type))
        await ctx.send("Status updated")

    @commands.command()
    async def reloadconfigs(self, ctx:commands.Context):
        async with ctx.typing():
            Configuration.loadGlobalConfig()
            await Configuration.onReady(self.bot)
            await ctx.send("Configs reloaded")

    @commands.command(hidden=True)
    async def eval(self, ctx:commands.Context, *, code: str):
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
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with contextlib.redirect_stdout(out):
                ret = await func()
        except Exception as e:
            value = out.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = out.getvalue()
            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                await ctx.send(f'```py\n{value}{ret}\n```')


def setup(bot):
    bot.add_cog(Admin(bot))