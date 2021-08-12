import asyncio
import contextlib
import io
import textwrap
import traceback
import datetime
from time import time

import discord
from discord.ext import commands, tasks
from discord.utils import time_snowflake

from Bot.TheRealGearBot import fill_cache
from Cogs.BaseCog import BaseCog
from Util import GearbotLogging, Utils, Configuration, Pages, Emoji, MessageUtils, Update, DocUtils, Translator
from Util.Converters import UserID, Guild, DiscordUser
from database.DatabaseConnector import LoggedMessage, LoggedAttachment
from views import SimplePager


class Admin(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.db_cleaner.start()
        self.cache_guardian.start()

    def cog_unload(self):
        self.db_cleaner.cancel()

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
            pipe = self.bot.redis_pool.pipeline()
            k = f'eval:{ctx.message.id}'
            pipe.set(k, output)
            pipe.expire(k, 7*24*60*60)
            await pipe.execute()
            pages = Pages.paginate(output, prefix='```py\n', suffix='```')
            content, view, _ = SimplePager.get_parts(pages, 0, ctx.guild.id if ctx.guild is not None else 0, f'eval:{ctx.message.id}')
            await ctx.send(f'Eval output 1/{len(pages)}{content}', view=view)
        else:
            await ctx.message.add_reaction(Emoji.get_emoji("YES"))

    async def init_eval(self, ctx, pages, **kwargs):
        pages = pages.split("----NEW PAGE----")
        page = pages[0]
        num = len(pages)
        return f"**Eval output 1/{num}**\n```py\n{page}```", None, num > 1,


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

    @commands.command()
    async def reset_cache(self, ctx):
        await MessageUtils.send_to(ctx, "YES", f"Cache reset initiated", translate=False)
        asyncio.create_task(fill_cache(self.bot))

    @commands.command()
    async def thread_migration(self, ctx):
        await MessageUtils.send_to(ctx, "LOADING", "Thread migration initiated", translate=False)
        for guild in self.bot.guilds:
            role_id = Configuration.get_var(guild.id, 'ROLES', 'MUTE_ROLE')
            if role_id != 0:
                role = guild.get_role(role_id)
                if role is not None:
                    for category in guild.categories:
                        if category.permissions_for(guild.me).manage_channels:
                            try:
                                current = category.overwrites_for(role)
                                current.update(use_threads=False, use_private_threads=False)
                                if not current.is_empty():
                                    await category.set_permissions(role, reason='thread release migration',overwrite=current)
                            except discord.Forbidden:
                                await asyncio.sleep(0.1)

                    # sleep a bit so we have time to receive the update events
                    await asyncio.sleep(2)

                    for channel in guild.text_channels:
                        if channel.permissions_for(guild.me).manage_channels:
                            if not channel.overwrites_for(role).is_empty():
                                try:
                                    current = channel.overwrites_for(role)
                                    current.update(use_threads=False, use_private_threads=False)
                                    if not current.is_empty():
                                        await channel.set_permissions(role, reason='thread release migration',overwrite=current)
                                except discord.Forbidden:
                                    pass
        await MessageUtils.send_to(ctx, 'YES', 'Thread migration completed!', translate=False)

    @tasks.loop(hours=1)
    async def db_cleaner(self):
        if Configuration.get_master_var("purge_db", True):
            # purge all messages older then 6 weeks
            snowflake = time_snowflake(datetime.datetime.utcfromtimestamp(time() - 60*60*24*7*6).replace(tzinfo=datetime.timezone.utc))
            purged_attachments = await LoggedAttachment.filter(id__lt=snowflake).delete()
            purged = await LoggedMessage.filter(messageid__lt=snowflake).delete()
            GearbotLogging.info(f"Purged {purged} old messages and {purged_attachments} attachments")

    @tasks.loop(minutes=3)
    async def cache_guardian(self):
        if not self.bot.chunker_active and self.bot.is_ready():
            min_cached_users = Configuration.get_master_var("min_cached_users", 0)
            if min_cached_users != 0 and min_cached_users > len(self.bot.users):
                await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('WARNING')} Incomplete cache detected, resetting to try and recover")
                await fill_cache(self.bot)




def setup(bot):
    bot.add_cog(Admin(bot))
