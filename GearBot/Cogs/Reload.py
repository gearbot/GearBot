import asyncio
import importlib
import os
import subprocess
from subprocess import Popen

from discord.ext import commands

import Util
from Util import GearbotLogging, Emoji, Translator


class Reload:

    def __init__(self, bot):
        self.bot:commands.Bot = bot

    async def __local_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)

    @commands.command(hidden=True)
    async def reload(self, ctx, *, cog: str):
        cogs = []
        for c in ctx.bot.cogs:
            cogs.append(c.replace('Cog', ''))

        if cog in cogs:
            self.bot.unload_extension(f"Cogs.{cog}")
            self.bot.load_extension(f"Cogs.{cog}")
            await ctx.send(f'**{cog}** has been reloaded.')
            await GearbotLogging.logToBotlog(f'**{cog}** has been reloaded by {ctx.author.name}.', log=True)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} I can't find that cog.")

    @commands.command(hidden=True)
    async def load(self, ctx, cog: str):
        if os.path.isfile(f"Cogs/{cog}.py") or os.path.isfile(f"GearBot/Cogs/{cog}.py"):
            self.bot.load_extension(f"Cogs.{cog}")
            await ctx.send(f"**{cog}** has been loaded!")
            await GearbotLogging.logToBotlog(f"**{cog}** has been loaded by {ctx.author.name}.", log=True)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} I can't find that cog.")

    @commands.command(hidden=True)
    async def unload(self, ctx, cog: str):
        if cog in ctx.bot.cogs:
            self.bot.unload_extension(f"Cogs.{cog}")
            await ctx.send(f'**{cog}** has been unloaded.')
            await GearbotLogging.logToBotlog(f'**{cog}** has been unloaded by {ctx.author.name}')
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} I can't find that cog.")

    @commands.command(hidden=True)
    async def hotreload(self, ctx:commands.Context):
        async with ctx.typing():
            await GearbotLogging.logToBotlog("Hot reload in progress...")
            utils = importlib.reload(Util)
            await utils.reload(self.bot)
            await GearbotLogging.logToBotlog("Reloading all cogs...")
            temp = []
            for cog in ctx.bot.cogs:
                temp.append(cog)
            for cog in temp:
                self.bot.unload_extension(f"Cogs.{cog}")
                GearbotLogging.info(f'{cog} has been unloaded.')
                self.bot.load_extension(f"Cogs.{cog}")
                GearbotLogging.info(f'{cog} has been loaded.')
            await GearbotLogging.logToBotlog("Hot reload complete.")
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} Hot reload complete.")
        await Translator.upload()

    @commands.command()
    async def pull(self, ctx):
        """Pulls from github so an upgrade can be performed without full restart"""
        async with ctx.typing():
            p = Popen(["git pull origin master"], cwd=os.getcwd(), shell=True, stdout=subprocess.PIPE)
            while p.poll() is None:
                await asyncio.sleep(1)
            out, error = p.communicate()
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} Pull completed with exit code {p.returncode}```yaml\n{out.decode('utf-8')}```")

def setup(bot):
    bot.add_cog(Reload(bot))