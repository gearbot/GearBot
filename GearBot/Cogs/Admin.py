import contextlib
import io
import textwrap
import traceback

import discord
from discord.ext import commands

from Cogs.BaseCog import BaseCog
from Util import GearbotLogging, Utils, Configuration, Pages, Emoji, MessageUtils, Update, DocUtils
from Util.Converters import UserID, Guild, DiscordUser


class Admin(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        Pages.register("eval", self.init_eval, self.update_eval)

    def cog_unload(self):
        Pages.unregister("eval")

    async def cog_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author) or ctx.author.id in Configuration.get_master_var("BOT_ADMINS", [])

    @commands.command()
    async def commandlist(self, ctx):
        await DocUtils.generate_command_list2(self.bot, ctx.message)


    @commands.command(hidden=True)
    async def restart(self, ctx):
        """Restarts the bot"""
        await ctx.send("Restarting...")
        await Utils.cleanExit(self.bot, ctx.author.name)


    @commands.command(hidden=True)
    async def upgrade(self, ctx):
        await ctx.send(
            f"{Emoji.get_chat_emoji('WRENCH')} I'll be right back with new gears! {Emoji.get_chat_emoji('WOOD')} {Emoji.get_chat_emoji('STONE')} {Emoji.get_chat_emoji('IRON')} {Emoji.get_chat_emoji('GOLD')} {Emoji.get_chat_emoji('DIAMOND')}")
        await Update.upgrade(ctx.author.name, self.bot)



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
            await Pages.create_new(self.bot, "eval", ctx, pages="----NEW PAGE----".join(Pages.paginate(output)), code=code, trigger=ctx.message.id, sender=ctx.author.id)
        else:
            await ctx.message.add_reaction(Emoji.get_emoji("YES"))

    async def init_eval(self, ctx, pages, **kwargs):
        pages = pages.split("----NEW PAGE----")
        page = pages[0]
        num = len(pages)
        return f"**Eval output 1/{num}**\n```py\n{page}```", None, num > 1,

    async def update_eval(self, ctx, message, page_num, action, data):
        if action == "REFRESH" and ctx is not None:
            await ctx.invoke(self.eval, code=data.get("code"))
        pages = data["pages"].split("----NEW PAGE----")
        page, page_num = Pages.basic_pages(pages, page_num, action)
        data["page"] = page_num
        return f"**Eval output {page_num + 1}/{len(pages)}**\n```py\n{page}```", None, data


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

    @commands.command()
    async def update(self, ctx):
        await ctx.invoke(self.bot.get_command("pull"))
        await ctx.invoke(self.bot.get_command("hotreload"))

    @commands.command()
    async def block_server(self, ctx, guild: Guild):
        blocked = Configuration.get_persistent_var("server_blocklist", [])
        blocked.append(guild.id)
        Configuration.set_persistent_var("server_blocklist", blocked)
        await guild.leave()
        await MessageUtils.send_to(ctx, "YES", f"{Utils.escape_markdown(guild.name)} (``{guild.id}``) has been added to the blocked servers list", translate=False)
        await GearbotLogging.bot_log(
            f"{Utils.escape_markdown(guild.name)} (``{guild.id}``) has been added to the blocked server list by {Utils.clean_user(ctx.author)}")

    @commands.command()
    async def block_user(self, ctx, user:DiscordUser):
        for guild in self.bot.guilds:
            if guild.owner is not None and guild.owner.id == user.id:
                await guild.leave()
        blocked = Configuration.get_persistent_var("user_blocklist", [])
        blocked.append(user.id)
        Configuration.set_persistent_var("user_blocklist", blocked)
        await MessageUtils.send_to(ctx, "YES", f"{Utils.clean_user(user)} (``{user.id}``) has been added to the blocked users list", translate=False)
        await GearbotLogging.bot_log(f"{Utils.clean_user(user)} (``{user.id}``) has been added to the blocked users list by {Utils.clean_user(ctx.author)}")

    @commands.command()
    async def pendingchanges(self, ctx):
        await ctx.send(f'https://github.com/gearbot/GearBot/compare/{self.bot.version}...master')




def setup(bot):
    bot.add_cog(Admin(bot))
