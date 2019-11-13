import importlib
import os

from discord.ext import commands

from Bot import TheRealGearBot, Reloader
from Cogs.BaseCog import Gear
from Util import GearbotLogging, Emoji, Translator, Utils, Pages, Configuration, DocUtils, Update


class Reload(Gear):

    def __init__(self, bot):
        super().__init__(bot)
        Pages.register("pull", self.init_pull, self.update_pull)

    async def cog_check (self, ctx):
        return await ctx.bot.is_owner(ctx.author) or ctx.author.id in Configuration.get_master_var("BOT_ADMINS", [])

    @commands.command(hidden=True)
    async def reload(self, ctx, *, cog: str):
        cogs = []
        for c in ctx.bot.cogs:
            cogs.append(c.replace('Cog', ''))

        if cog in cogs:
            self.bot.unload_extension(f"Cogs.{cog}")
            self.bot.load_extension(f"Cogs.{cog}")
            await ctx.send(f'**{cog}** has been reloaded.')
            await GearbotLogging.bot_log(f'**{cog}** has been reloaded by {ctx.author.name}.')
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
        ctx_message = await ctx.send(f"{Emoji.get_chat_emoji('REFRESH')}  Hot reload in progress...")
        await Update.update(ctx.author.name, self.bot)
        m = f"{Emoji.get_chat_emoji('YES')} Hot reload complete, now running on {self.bot.version}"
        await ctx_message.edit(content=m)

    @commands.command()
    async def update_site(self, ctx):
        GearbotLogging.info("Site update initiated")
        message = await ctx.send(f"{Emoji.get_chat_emoji('REFRESH')} Updating site")
        await DocUtils.generate_command_list(ctx.bot, message)
        cloudflare_info = Configuration.get_master_var("CLOUDFLARE", {})
        if 'ZONE' in cloudflare_info:
            headers = {
                "X-Auth-Email": cloudflare_info["EMAIL"],
                "X-Auth-Key": cloudflare_info["KEY"],
                "Content-Type": "application/json"
            }
            async with self.bot.aiosession.post(
                    f"https://api.cloudflare.com/client/v4/zones/{cloudflare_info['ZONE']}/purge_cache",
                    json=dict(purge_everything=True), headers=headers) as reply:
                content = await reply.json()
                GearbotLogging.info(f"Cloudflare purge response: {content}")
                if content["success"]:
                    await message.edit(content=f"{Emoji.get_chat_emoji('YES')} Site has been updated and cloudflare cache has been purged")
                else:
                    await message.edit(content=f"{Emoji.get_chat_emoji('NO')} Cloudflare cache purge failed")

    @commands.command()
    async def pull(self, ctx):
        """Pulls from github so an upgrade can be performed without full restart"""
        async with ctx.typing():
            code, out, error = await Utils.execute(["git pull origin master"])
        if code is 0:
            await Pages.create_new(self.bot, "pull", ctx, title=f"{Emoji.get_chat_emoji('YES')} Pull completed with exit code {code}", pages="----NEW PAGE----".join(Pages.paginate(out)))
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} Pull completed with exit code {code}```yaml\n{out}\n{error}```")

    async def init_pull(self, ctx, title, pages):
        pages = pages.split("----NEW PAGE----")
        page = pages[0]
        num = len(pages)
        return f"**{title} (1/{num})**\n```yaml\n{page}```", None, num > 1,

    async def update_pull(self, ctx, message, page_num, action, data):
        pages = data["pages"].split("----NEW PAGE----")
        title = data["title"]
        page, page_num = Pages.basic_pages(pages, page_num, action)
        data["page"] = page_num
        return f"**{title} ({page_num + 1}/{len(pages)})**\n```yaml\n{page}```", None, data

def setup(bot):
    bot.add_cog(Reload(bot))