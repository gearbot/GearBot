import asyncio
import concurrent
import json
import os
import signal
from concurrent.futures._base import CancelledError

import sys
import time
import traceback
import datetime

import aiohttp
import aioredis
import disnake
import sentry_sdk
from aiohttp import ClientOSError, ServerDisconnectedError
from disnake import Activity, Embed, Colour, Message, TextChannel, Forbidden, ConnectionClosed, Guild, NotFound
from disnake.abc import PrivateChannel
from disnake.ext import commands
from disnake.ext.commands import UnexpectedQuoteError, ExtensionAlreadyLoaded, InvalidEndOfQuotedStringError

from Util import Configuration, GearbotLogging, Emoji, Pages, Utils, Translator, InfractionUtils, MessageUtils, \
    server_info, DashConfig
from Util.Configuration import ConfigNotLoaded
from Util.Permissioncheckers import NotCachedException
from Util.Utils import to_pretty_time
from database import DatabaseConnector, DBUtils
from views.InfSearch import InfSearch


def prefix_callable(bot, message):
    user_id = bot.user.id
    prefixes = [f'<@!{user_id}> ', f'<@{user_id}> '] #execute commands by mentioning
    if message.guild is None:
        prefixes.append('!') #use default ! prefix in DMs
    elif bot.STARTUP_COMPLETE:
        prefixes.append(Configuration.legacy_get_var(message.guild.id, "GENERAL", "PREFIX"))
    return prefixes



async def on_ready(bot):
    await fill_cache(bot)


async def fill_cache(bot):
    await asyncio.wait_for(actually_fill_cache(bot), 60*25)

async def actually_fill_cache(bot):
    # don't try to start a new one when one is already pending
    if bot.chunker_pending:
        return

    await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('REFRESH')} Cluster {bot.cluster} cache reset initiated")

    # claim the pending spot
    bot.chunker_pending = True
    # terminate running queue if needed
    count = 0
    while bot.chunker_active:
        bot.chunker_should_terminate = True
        await asyncio.sleep(0.5)
        count += 1
        if count > 120:
            await GearbotLogging.bot_log("Failure to reset the chunker after a reconnect, assuming it is stuck and proceeding with the chunking to attempt to recover.")
            break

    # we are now the active chunker
    bot.chunker_pending = False
    bot.chunker_active = True
    bot.chunker_should_terminate = False

    # grab a copy of the current guild list as this can mutate while we work
    guild_ids = [guild.id for guild in bot.guilds]

    await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('LOADING')} Cache population in progress on cluster {bot.cluster}, fetching users from {len(bot.guilds)} guilds")

    # chunk them all
    # TODO: split per shard if this turns out to be too slow but the distribution between shards should be fairly even so the performance impact should be limited
    done = 0
    for gid in guild_ids:
        if bot.chunker_should_terminate is True:
            return
        guild = bot.get_guild(gid)
        if guild is None:
            GearbotLogging.info(f"Tried to fetch {gid} for chunking but it no longer exists, assuming we where removed or it went unavailable")
        else:
            await guild.chunk(cache=True)
            await asyncio.sleep(0.1)
            done += 1
    bot.chunker_active = False
    if bot.chunker_should_terminate:
        await GearbotLogging.bot_log(
            f"{Emoji.get_chat_emoji('WARNING')} Cache population aborted for cluster {bot.cluster} with {len(guild_ids) - done} left to go!")
    else:
        await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('YES')} Cache population completed for cluster {bot.cluster}!")


async def message_flusher():
    while True:
        await asyncio.sleep(60)
        await DBUtils.flush()

async def on_message(bot, message:Message):
    if message.author.bot:
        if message.author.id == bot.user.id:
            bot.self_messages += 1
        else:
            bot.bot_messages += 1
        return
    ctx: commands.Context = await bot.get_context(message)
    bot.user_messages += 1
    if ctx.valid and ctx.command is not None:
        bot.commandCount = bot.commandCount + 1
        if isinstance(ctx.channel, TextChannel) and (not ctx.channel.permissions_for(ctx.channel.guild.me).send_messages):
            try:
                await ctx.author.send("Hey, you tried triggering a command in a channel I'm not allowed to send messages in. Please grant me permissions to reply and try again.")
            except Forbidden:
                pass  # closed DMs
        elif ctx.author.id in Configuration.get_persistent_var("user_blocklist", []):
            try:
                if message.channel.permissions_for(ctx.channel.guild.me).send_messages:
                    await MessageUtils.send_to(ctx, "BAD_USER", "You have been globally blocked from using this bot due to abuse", translate=False)
            except Forbidden:
                pass  # closed DMs
        else:
            await bot.invoke(ctx)

async def on_connect(bot):
    await Configuration.load_bulk([guild.id for guild in bot.guilds])


async def on_guild_join(bot, guild: Guild):
    blocked = Configuration.get_persistent_var("server_blocklist", [])
    if guild.id in blocked:
        GearbotLogging.info(f"Someone tried to add me to blocked guild {guild.name} ({guild.id})")
        try:
            await guild.owner.send("Someone tried adding me to {guild.name} (``{guild.id}``) but the server has been blocked")
        except Exception:
            pass
        await guild.leave()
    elif guild.owner_id in Configuration.get_persistent_var("user_blocklist", []):
        GearbotLogging.info(f"Someone tried to add me to {Utils.clean(guild.name)} ({guild.id}) but the owner ({guild.owner} ({guild.owner_id})) is blocked")
        try:
            await (await bot.fetch_user(guild.owner_id)).send(f"Someone tried adding me to {guild.name} (``{guild.id}``) but you have been blocked due to bot abuse, so i left")
        except Exception:
            pass
        await guild.leave()
    else:
        GearbotLogging.info(f"A new guild came up: {guild.name} ({guild.id}).")
        await Configuration.load_config(guild.id)
        name = await Utils.clean(guild.name)
        await guild.chunk(cache=True)
        await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('JOIN')} A new guild came up: {name} ({guild.id}).", embed=server_info.server_info_embed(guild))

async def on_guild_remove(bot, guild):
    blocked = Configuration.get_persistent_var("server_blocklist", [])
    blocked_users = Configuration.get_persistent_var("user_blocklist", [])
    if guild.id not in blocked and guild.owner_id not in blocked_users:
        GearbotLogging.info(f"I was removed from a guild: {guild.name} ({guild.id}).")
        bot.metrics.bot_guilds.labels(cluster=bot.cluster).dec()
        await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('LEAVE')} I was removed from a guild: {guild.name} ({guild.id}).", embed=server_info.server_info_embed(guild))


async def on_guild_update(before, after):
    if after.owner is not None and after.owner_id in Configuration.get_persistent_var("user_blocklist", []):
        GearbotLogging.info(
            f"Someone transferred {after.name} ({after.id}) to ({after.owner} ({after.owner_id})) but they are blocked")
        try:
            await after.owner.send(f"Someone transferred {after.name} (``{after.id}``) to you, but you have been blocked due to bot abuse, so i left")
        except Exception:
            pass
        await after.leave()

class PostParseError(commands.BadArgument):

    def __init__(self, type, error):
        super().__init__(None)
        self.type = type
        self.error=error


async def on_command_error(bot, ctx: commands.Context, error):
    if isinstance(error, ConfigNotLoaded):
        return
    if isinstance(error, NotCachedException):
        if bot.loading_task is not None:
            if bot.initial_fill_complete:
                await send(ctx, f"{Emoji.get_chat_emoji('CLOCK')} Due to a earlier connection failure the cached data for this guild is no longer up to date and is being rebuild. Please try again in a few minutes.")
            else:
                await send(ctx, f"{Emoji.get_chat_emoji('CLOCK')} GearBot is in the process of starting up and has not received the member info for this guild. Please try again in a few minutes.")
        else:
            await send(ctx, f"{Emoji.get_chat_emoji('CLOCK')} GearBot only just joined this guild and is still receiving the initial member info for this guild, please try again in a few seconds")
    if isinstance(error, commands.BotMissingPermissions):
        GearbotLogging.error(f"Encountered a permission error while executing {ctx.command}: {error}")
        await send(ctx, error)
    elif isinstance(error, commands.CheckFailure):
        if ctx.command.qualified_name != "latest" and ctx.guild is not None and await Configuration.get_var(ctx.guild.id, "GENERAL", "PERM_DENIED_MESSAGE"):
            await MessageUtils.send_to(ctx, 'LOCK', 'permission_denied')
    elif isinstance(error, commands.CommandOnCooldown):
        await send(ctx, error)
    elif isinstance(error, commands.MissingRequiredArgument):
        param = list(ctx.command.params.values())[min(len(ctx.args) + len(ctx.kwargs), len(ctx.command.params))]
        bot.help_command.context = ctx
        await send(ctx,
            f"{Emoji.get_chat_emoji('NO')} {Translator.translate('missing_arg', ctx, arg=param._name, error=Utils.replace_lookalikes(str(error)))}\n{Emoji.get_chat_emoji('WRENCH')} {Translator.translate('command_usage', ctx, usage=bot.help_command.get_command_signature(ctx.command))}")
    elif isinstance(error, PostParseError):
        bot.help_command.context = ctx
        await send(ctx, f"{Emoji.get_chat_emoji('NO')} {Translator.translate('bad_argument', ctx, type=error.type, error=Utils.replace_lookalikes(str(error.error)))}\n{Emoji.get_chat_emoji('WRENCH')} {Translator.translate('command_usage', ctx, usage=bot.help_command.get_command_signature(ctx.command))}")
    elif isinstance(error, commands.BadArgument):
        param = list(ctx.command.params.values())[min(len(ctx.args) + len(ctx.kwargs), len(ctx.command.params))]
        bot.help_command.context = ctx
        await send(ctx, f"{Emoji.get_chat_emoji('NO')} {Translator.translate('bad_argument', ctx, type=param._name, error=Utils.replace_lookalikes(str(error)))}\n{Emoji.get_chat_emoji('WRENCH')} {Translator.translate('command_usage', ctx, usage=bot.help_command.get_command_signature(ctx.command))}")
    elif isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, NotFound):
        e = Emoji.get_chat_emoji('BUG')
        await send(ctx, f"{e} Command failed because the discord api responded with \"not found\" If you didn't delete anything manually and this keeps happening please report it on support server (DM me ``!about`` or check the website for an invite) {e}")
    elif isinstance(error, Forbidden):
        e = Emoji.get_chat_emoji('BUG')
        await ctx.send(f"{e} Command failed because the discord api responded with \"forbidden\" reply. Please make sure the bot has the permissions and roles required to perform this command {e}")
    elif isinstance(error, UnexpectedQuoteError) or isinstance(error, InvalidEndOfQuotedStringError):
        e = Emoji.get_chat_emoji('BUG')
        await ctx.send(f"{e} Command parsing failed, unexpected or unclosed quote encountered {e}")

    else:
        await handle_exception("Command execution failed", bot, error.original if hasattr(error, "original") else error, ctx=ctx)
        # notify caller
        e = Emoji.get_chat_emoji('BUG')
        if ctx.channel.permissions_for(ctx.me).send_messages:
            await ctx.send(f"{e} Something went wrong while executing that command. If this keeps happening please report it on support server (DM me ``!about`` or check the website for an invite) {e}")


async def send(ctx, *args, **kwargs):
    if ctx.channel.permissions_for(ctx.me).send_messages:
        await ctx.send(*args, **kwargs)

def extract_info(o):
    info = ""
    if hasattr(o, "__dict__"):
        info += str(o.__dict__)
    elif hasattr(o, "__slots__"):
        items = dict()
        for slot in o.__slots__:
            try:
                items[slot] = getattr(o, slot)
            except AttributeError:
                pass
        info += str(items)
    else:
        info += str(o) + " "
    return info

async def on_error(bot, event, *args, **kwargs):
    t, exception, info = sys.exc_info()
    await handle_exception("Event handler failure", bot, exception, event, None, None, *args, **kwargs)

async def handle_database_error(bot):
    GearbotLogging.error(traceback.format_exc())
    # database trouble, notify bot owner
    message = f"{Emoji.get_chat_emoji('WARNING')} Peewee exception caught! attempting to reconnect to the database!"
    await GearbotLogging.message_owner(bot, message)
    await GearbotLogging.bot_log(message)

    try:
        DatabaseConnector.init()
        bot.database_connection = DatabaseConnector.connection
    except:
        # fail, trying again in 10 just in case the database is rebooting
        time.sleep(15)
        try:
            DatabaseConnector.init()
            bot.database_connection = DatabaseConnector.connection
        except:
            if os.path.isfile('stage_2.txt'):
                message = f"{Emoji.get_chat_emoji('NO')} VM reboot did not fix the problem, shutting down completely for fixes"
                await bot.get_user(bot.owner_id).dm_channel.send(message)
                await GearbotLogging.bot_log(message)
                with open("stage_3.txt", "w") as file:
                    file.write("stage_3")
                os.kill(os.getpid(), 9)
            elif os.path.isfile('stage_1.txt'):
                with open("stage_2.txt", "w") as file:
                    file.write("stage_2")
                message = f"{Emoji.get_chat_emoji('NO')} Reconnecting and bot rebooting failed, escalating to VM reboot"
                await GearbotLogging.message_owner(bot, message)
                await GearbotLogging.bot_log(message)
                data = {'type': 'reboot'}
                async with aiohttp.ClientSession(headers={'Content-Type': 'application/json',
                                                          'Authorization': f'Bearer {Configuration.get_master_var("DO_TOKEN")}'}) as session:
                    await session.post(f'https://api.digitalocean.com/v2/droplets/{Configuration.get_master_var("DO_ID")}/actions',
                                            data=json.dumps(data), timeout=30)
                time.sleep(60)

            else:
                message = f"{Emoji.get_chat_emoji('NO')} Reconnecting failed, escalating to reboot"
                await GearbotLogging.message_owner(bot, message)
                await GearbotLogging.bot_log(message)
                with open("stage_1.txt", "w") as file:
                    file.write("stage_1")
                os.kill(os.getpid(), 9)
        else:
            message = f"{Emoji.get_chat_emoji('YES')} 2nd reconnection attempt successfully connected!"
            await GearbotLogging.message_owner(bot, message)
            await GearbotLogging.bot_log(message)
    else:
        message = f"{Emoji.get_chat_emoji('YES')} 1st reconnection attempt successfully connected!"
        await GearbotLogging.message_owner(bot, message)
        await GearbotLogging.bot_log(message)



async def handle_exception(exception_type, bot, exception, event=None, message=None, ctx = None, *args, **kwargs):
    if bot is not None:
        bot.errors = bot.errors + 1
    with sentry_sdk.push_scope() as scope:
        embed = Embed(colour=Colour(0xff0000), timestamp=datetime.datetime.utcfromtimestamp(time.time()).replace(tzinfo=datetime.timezone.utc))

        # something went wrong and it might have been in on_command_error, make sure we log to the log file first
        lines = [
            "\n===========================================EXCEPTION CAUGHT, DUMPING ALL AVAILABLE INFO===========================================",
            f"Type: {exception_type}"
        ]

        arg_info = ""
        for arg in list(args):
            arg_info += extract_info(arg) + "\n"
        if arg_info == "":
            arg_info = "No arguments"

        kwarg_info = ""
        for name, arg in kwargs.items():
            kwarg_info += "{}: {}\n".format(name, extract_info(arg))
        if kwarg_info == "":
            kwarg_info = "No keyword arguments"

        lines.append("======================Exception======================")
        lines.append(f"{str(exception)} ({type(exception)})")

        lines.append("======================ARG INFO======================")
        lines.append(arg_info)
        sentry_sdk.add_breadcrumb(category='arg info', message=arg_info, level='info')

        lines.append("======================KWARG INFO======================")
        lines.append(kwarg_info)
        sentry_sdk.add_breadcrumb(category='kwarg info', message=kwarg_info, level='info')


        lines.append("======================STACKTRACE======================")
        tb = "".join(traceback.format_tb(exception.__traceback__))
        lines.append(tb)

        if message is None and event is not None and hasattr(event, "message"):
            message = event.message

        if message is None and ctx is not None:
            message = ctx.message

        if message is not None and hasattr(message, "content"):
            lines.append("======================ORIGINAL MESSAGE======================")
            lines.append(message.content)
            if message.content is None or message.content == "":
                content = "<no content>"
            else:
                content = message.content
            scope.set_tag('message content', content)
            embed.add_field(name="Original message", value=Utils.trim_message(content, 1000), inline=False)

            lines.append("======================ORIGINAL MESSAGE (DETAILED)======================")
            lines.append(extract_info(message))

        if event is not None:
            lines.append("======================EVENT NAME======================")
            lines.append(event)
            scope.set_tag('event name', event)
            embed.add_field(name="Event", value=event)


        if ctx is not None:
            lines.append("======================COMMAND INFO======================")

            lines.append(f"Command: {ctx.command.name}")
            embed.add_field(name="Command", value=ctx.command.name)
            scope.set_tag('command', ctx.command.name)

            channel_name = 'Private Message' if isinstance(ctx.channel, PrivateChannel) else f"{ctx.channel.name} (`{ctx.channel.id}`)"
            lines.append(f"Channel: {channel_name}")
            embed.add_field(name="Channel", value=channel_name, inline=False)
            scope.set_tag('channel', channel_name)

            sender = f"{str(ctx.author)} (`{ctx.author.id}`)"
            scope.user = dict(id=ctx.author.id, username=str(ctx.author))
            lines.append(f"Sender: {sender}")
            embed.add_field(name="Sender", value=sender, inline=False)

        lines.append("===========================================DATA DUMP COMPLETE===========================================")
        GearbotLogging.error("\n".join(lines))



        for t in [ConnectionClosed, ClientOSError, ServerDisconnectedError, ConfigNotLoaded]:
            if isinstance(exception, t):
                return
        #nice embed for info on discord


        embed.set_author(name=exception_type)
        embed.add_field(name="Exception", value=f"{str(exception)} (`{type(exception)}`)", inline=False)
        parts = Pages.paginate(tb, max_chars=1024)
        num = 1
        for part in parts:
            embed.add_field(name=f"Traceback {num}/{len(parts)}", value=part)
            num += 1
        sentry_sdk.capture_exception(exception)
    # try logging to botlog, wrapped in an try catch as there is no higher lvl catching to prevent taking down the bot (and if we ended here it might have even been due to trying to log to botlog
    try:
        await GearbotLogging.bot_log(embed=embed)
    except Exception as ex:
        GearbotLogging.error(
            f"Failed to log to botlog, either Discord broke or something is seriously wrong!\n{ex}")
        GearbotLogging.error(traceback.format_exc())
