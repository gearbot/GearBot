import asyncio
import os

from discord.ext import commands

from Util import GearbotLogging
from database.DatabaseConnector import LoggedMessage


class Admin:

    def __init__(self, bot):
        self.bot:commands.Bot = bot

    async def __local_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)


    @commands.command()
    async def restart(self, ctx):
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
        else:
            await ctx.send(f"I can't find that cog.")

    @commands.command(hidden=True)
    async def load(self, ctx, cog: str):
        if os.path.isfile(f"Cogs/{cog}.py"):
            self.bot.load_extension(f"Cogs.{cog}")
            await ctx.send(f"**{cog}** has been loaded!")
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
        else:
            await ctx.send(f"I can't find that cog.")

    @commands.command()
    async def test(self, ctx, id:str):
        message = LoggedMessage.get_by_id(id)
        await ctx.send(message.content)

    @commands.command()
    async def upgrade(self, ctx):
        await ctx.send("<:BCWrench:344163417981976578> I'll be right back with new gears! <:woodGear:344163118089240596> <:stoneGear:344163146325295105> <:ironGear:344163170664841216> <:goldGear:344163202684289024> <:diamondGear:344163228101640192>")
        await GearbotLogging.logToBotlog(f"Upgrade initiated by {ctx.author.name}")
        file = open("upgradeRequest", "w")
        file.write("upgrade requested")
        file.close()
        await self.bot.logout()
        await self.bot.close()
        await asyncio.sleep(11)

def setup(bot):
    bot.add_cog(Admin(bot))