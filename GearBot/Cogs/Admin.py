import asyncio
import os
import subprocess
from datetime import datetime
from subprocess import Popen

import discord
from discord.ext import commands

from Util import GearbotLogging, Util


class Admin:

    def __init__(self, bot):
        self.bot:commands.Bot = bot

    async def __local_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)


    @commands.command(hidden=True)
    async def restart(self, ctx):
        """Restarts the bot"""
        await ctx.send("Restarting...")
        await Util.cleanExit(self.bot, ctx.author.name)

    @commands.command(hidden=True)
    async def reload(self, ctx, *, cog: str):
        cogs = []
        for c in ctx.bot.cogs:
            cogs.append(c.replace('Cog', ''))

        if cog in cogs:
            self.bot.unload_extension(f"Cogs.{cog}")
            self.bot.load_extension(f"Cogs.{cog}")
            await ctx.send(f'**{cog}** has been reloaded')
            await GearbotLogging.logToBotlog(f'**{cog}** has been reloaded by {ctx.author.name}', log=True)
        else:
            await ctx.send(f"I can't find that cog.")

    @commands.command(hidden=True)
    async def load(self, ctx, cog: str):
        if os.path.isfile(f"Cogs/{cog}.py") or os.path.isfile(f"GearBot/Cogs/{cog}.py"):
            self.bot.load_extension(f"Cogs.{cog}")
            await ctx.send(f"**{cog}** has been loaded!")
            await GearbotLogging.logToBotlog(f"**{cog}** has been loaded by {ctx.author.name}", log=True)
        else:
            await ctx.send(f"I can't find that cog.")

    @commands.command(hidden=True)
    async def unload(self, ctx, cog: str):
        cogs = []
        for c in ctx.bot.cogs:
            cogs.append(c.replace('Cog', ''))

        if cog in cogs:
            self.bot.unload_extension(f"Cogs.{cog}")
            await ctx.send(f'**{cog}** has been unloaded')
            await GearbotLogging.logToBotlog(f'**{cog}** has been unloaded by {ctx.author.name}', log=True)
        else:
            await ctx.send(f"I can't find that cog.")

    @commands.command(hidden=True)
    async def upgrade(self, ctx):
        await ctx.send("<:BCWrench:344163417981976578> I'll be right back with new gears! <:woodGear:344163118089240596> <:stoneGear:344163146325295105> <:ironGear:344163170664841216> <:goldGear:344163202684289024> <:diamondGear:344163228101640192>")
        await GearbotLogging.logToBotlog(f"Upgrade initiated by {ctx.author.name}", log=True)
        file = open("upgradeRequest", "w")
        file.write("upgrade requested")
        file.close()
        await self.bot.logout()
        await self.bot.close()
        await asyncio.sleep(11)

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
        p = Popen(["git pull origin master"], cwd=os.getcwd(), shell=True, stdout=subprocess.PIPE)
        while p.poll() is None:
            await asyncio.sleep(1)
        out, error = p.communicate()
        await ctx.send(f"Pull completed with exit code {p.returncode}```{out}```")

    @commands.command()
    async def test(self, ctx):
        await ctx.send("<a:aMeowWave:394101112652693526>")

    @commands.command()
    async def setStatus(self, ctx, type:int, *, status:str):
        await self.bot.change_presence(activity=discord.Activity(name=status, type=type))
        await ctx.send("Status updated")

def setup(bot):
    bot.add_cog(Admin(bot))