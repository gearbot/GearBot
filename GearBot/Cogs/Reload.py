import importlib
import os

from discord.ext import commands

from Bot import TheRealGearBot, Reloader
from Bot.GearBot import GearBot
from Util import GearbotLogging, Emoji, Translator, DocUtils, Utils, Pages


class Reload:

    def __init__(self, bot):
        self.bot:GearBot = bot
        Pages.register("pull", self.init_pull, self.update_pull, sender_only=True)

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
            await GearbotLogging.bot_log(f'**{cog}** has been reloaded by {ctx.author.name}.', log=True)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} I can't find that cog.")

    @commands.command(hidden=True)
    async def load(self, ctx, cog: str):
        if os.path.isfile(f"Cogs/{cog}.py") or os.path.isfile(f"GearBot/Cogs/{cog}.py"):
            self.bot.load_extension(f"Cogs.{cog}")
            await ctx.send(f"**{cog}** has been loaded!")
            await GearbotLogging.bot_log(f"**{cog}** has been loaded by {ctx.author.name}.")
            GearbotLogging.info(f"{cog} has been loaded")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} I can't find that cog.")

    @commands.command(hidden=True)
    async def unload(self, ctx, cog: str):
        if cog in ctx.bot.cogs:
            self.bot.unload_extension(f"Cogs.{cog}")
            await ctx.send(f'**{cog}** has been unloaded.')
            await GearbotLogging.bot_log(f'**{cog}** has been unloaded by {ctx.author.name}')
            GearbotLogging.info(f"{cog} has been unloaded")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} I can't find that cog.")

    @commands.command(hidden=True)
    async def hotreload(self, ctx:commands.Context):
        message = await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('REFRESH')} Hot reload in progress...")
        ctx_message = await ctx.send(f"{Emoji.get_chat_emoji('REFRESH')}  Hot reload in progress...")
        GearbotLogging.info("Initiating hot reload")

        GearbotLogging.LOG_PUMP.running = False
        Utils.cache_task.running = False
        importlib.reload(Reloader)
        for c in Reloader.components:
            importlib.reload(c)
        GearbotLogging.info("Reloading all cogs...")
        temp = []
        for cog in self.bot.cogs:
            temp.append(cog)
        for cog in temp:
            self.bot.unload_extension(f"Cogs.{cog}")
            GearbotLogging.info(f'{cog} has been unloaded.')
            self.bot.load_extension(f"Cogs.{cog}")
            GearbotLogging.info(f'{cog} has been loaded.')

        await TheRealGearBot.initialize(self.bot)
        GearbotLogging.info("Hot reload complete.")
        m = f"{Emoji.get_chat_emoji('YES')} Hot reload complete"
        await message.edit(content=m)
        await ctx_message.edit(content=m)
        await Translator.upload()
        await DocUtils.update_docs(ctx.bot)
        self.bot.hot_reloading = False

    @commands.command()
    async def pull(self, ctx):
        """Pulls from github so an upgrade can be performed without full restart"""
        async with ctx.typing():
            code, out, error = await Utils.execute(["git pull origin master"])
        if code is 0:
            await Pages.create_new("pull", ctx, title=f"{Emoji.get_chat_emoji('YES')} Pull completed with exit code {code}", pages=Pages.paginate(out.decode('utf-8')))
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} Pull completed with exit code {code}```yaml\n{out.decode('utf-8')}\n{error.decode('utf-8')}```")

    async def init_pull(self, ctx, title, pages):
        page = pages[0]
        num = len(pages)
        return f"**{title} (1/{num})**\n```yaml\n{page}```", None, num > 1, []

    async def update_pull(self, ctx, message, page_num, action, data):
        pages = data["pages"]
        title = data["title"]
        page, page_num = Pages.basic_pages(pages, page_num, action)
        return f"**{title} ({page_num + 1}/{len(pages)})**\n```yaml\n{page}```", None, page_num

def setup(bot):
    bot.add_cog(Reload(bot))