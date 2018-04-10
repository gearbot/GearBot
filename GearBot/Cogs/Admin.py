import asyncio
import os
from datetime import datetime

from discord.ext import commands

from Util import GearbotLogging


class Admin:

    def __init__(self, bot):
        self.bot:commands.Bot = bot

    async def __local_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)


    @commands.command(hidden=True)
    async def restart(self, ctx):
        """Restarts the bot"""
        await ctx.send("Restarting...")
        await GearbotLogging.logToBotlog(f"Restart triggered by {ctx.author.name}", log=True)
        await self.bot.logout()
        await self.bot.close()
        await asyncio.sleep(11)

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
        if os.path.isfile(f"Cogs/{cog}.py"):
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
    async def uptime(self, ctx):
        uptime = datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        days, hours = divmod(hours, 24)
        minutes, seconds = divmod(remainder, 60)

        await ctx.send(f"<:gearDiamond:433284297345073153>  Gears have been spinning for {days} day, {hours} hours, {minutes} minutes and {seconds} seconds\n<:BCWrench:433284297181495298> {self.bot.messageCount} messages have been processed")

def setup(bot):
    bot.add_cog(Admin(bot))