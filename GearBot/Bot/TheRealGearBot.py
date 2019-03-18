import asyncio
import json
import os
import signal
import sys
import time
import traceback
from datetime import datetime

import aiohttp
import aioredis
import sentry_sdk
from discord import Activity, Embed, Colour, Message, TextChannel, Forbidden
from discord.abc import PrivateChannel
from discord.ext import commands
from peewee import PeeweeException

from Util import Configuration, GearbotLogging, Emoji, Pages, Utils, Translator, InfractionUtils, MessageUtils
from database import DatabaseConnector


def prefix_callable(bot, message):
    user_id = bot.user.id
    prefixes = [f'<@!{user_id}> ', f'<@{user_id}> '] #execute commands by mentioning
    if message.guild is None:
        prefixes.append('!') #use default ! prefix in DMs
    elif bot.STARTUP_COMPLETE:
        prefixes.append(Configuration.get_var(message.guild.id, "PREFIX"))
    return prefixes

async def initialize(bot):
    #lock event handling while we get ready
    bot.locked = True
    try:
        #database
        GearbotLogging.info("Connecting to the database.")
        DatabaseConnector.init()
        bot.database_connection = DatabaseConnector.connection
        GearbotLogging.info("Database connection established.")

        GearbotLogging.initialize_pump(bot)
        Emoji.initialize(bot)
        Utils.initialize(bot)
        Translator.initialize(bot)
        InfractionUtils.initialize(bot)
        bot.data = {
            "forced_exits": set(),
            "unbans": set(),
            "message_deletes": set()
        }
        await GearbotLogging.initialize(bot, Configuration.get_master_var("BOT_LOG_CHANNEL"))

        if bot.redis_pool is None or not hasattr(bot, 'redis_raid_pool'):
            try:
                socket = Configuration.get_master_var("REDIS_SOCKET", "")
                if socket == "":
                    bot.redis_pool = await aioredis.create_redis_pool((Configuration.get_master_var('REDIS_HOST', "localhost"), Configuration.get_master_var('REDIS_PORT', 6379)), encoding="utf-8", db=0)
                else:
                    bot.redis_pool = await aioredis.create_redis_pool(socket, encoding="utf-8", db=0)
            except OSError:
                GearbotLogging.error("==============Failed to connect to redis==============")
                await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('NO')} Failed to connect to redis, caching unavailable")
            else:
                GearbotLogging.info("Redis connection established")
                await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('YES')} Redis connection established, let's go full speed!")

        if bot.aiosession is None:
            bot.aiosession = aiohttp.ClientSession()
        bot.being_cleaned.clear()
        await Configuration.initialize(bot)
    except Exception as ex:
        #make sure we always unlock, even when something went wrong!
        bot.locked = False
        raise ex
    bot.locked = False



async def on_ready(bot):
    if not bot.STARTUP_COMPLETE:
        await initialize(bot)
        #shutdown handler for clean exit on linux
        try:
            for signame in ('SIGINT', 'SIGTERM'):
                asyncio.get_event_loop().add_signal_handler(getattr(signal, signame),
                                        lambda: asyncio.ensure_future(Utils.cleanExit(bot, signame)))
        except Exception:
            pass #doesn't work on windows

        bot.start_time = datetime.utcnow()
        GearbotLogging.info("Loading cogs...")
        for extension in Configuration.get_master_var("COGS"):
            try:
                bot.load_extension("Cogs." + extension)
            except Exception as e:
                await handle_exception(f"Failed to load cog {extension}", bot, e)
        GearbotLogging.info("Cogs loaded")

        to_unload = Configuration.get_master_var("DISABLED_COMMANDS", [])
        for c in to_unload:
            bot.remove_command(c)

        if Configuration.get_master_var("CROWDIN") is not None:
            bot.loop.create_task(translation_task(bot))

        bot.STARTUP_COMPLETE = True
        info = await bot.application_info()
        bot.loop.create_task(keepDBalive(bot))  # ping DB every hour so it doesn't run off
        gears = [Emoji.get_chat_emoji(e) for e in ["WOOD", "STONE", "IRON", "GOLD", "DIAMOND"]]
        a = " ".join(gears)
        b = " ".join(reversed(gears))
        await GearbotLogging.bot_log(message=f"{a} All gears turning at full speed, {info.name} ready to go! {b}")
        await bot.change_presence(activity=Activity(type=3, name='the gears turn'))
    else:
        await bot.change_presence(activity=Activity(type=3, name='the gears turn'))


async def keepDBalive(bot):
    while not bot.is_closed():
        bot.database_connection.connection().ping(True)
        await asyncio.sleep(3600)


async def translation_task(bot):
    while not bot.is_closed():
        try:
            await Translator.update()
        except Exception as ex:
            await handle_exception("Translation task", bot, ex)

        try:
            await asyncio.sleep(6*60*60)
        except asyncio.CancelledError:
            pass # bot shutting down


async def on_message(bot, message:Message):
    if message.author.bot:
        if message.author.id == bot.user.id:
            bot.self_messages += 1
        bot.bot_messages += 1
        return
    ctx: commands.Context = await bot.get_context(message)
    bot.user_messages += 1
    if ctx.valid and ctx.command is not None:
        bot.commandCount = bot.commandCount + 1
        if isinstance(ctx.channel, TextChannel) and not ctx.channel.permissions_for(ctx.channel.guild.me).send_messages:
            try:
                await ctx.author.send("Hey, you tried triggering a command in a channel I'm not allowed to send messages in. Please grant me permissions to reply and try again.")
            except Forbidden:
                pass #closed DMs
        else:
            await bot.invoke(ctx)


async def on_guild_join(guild):
    GearbotLogging.info(f"A new guild came up: {guild.name} ({guild.id}).")
    Configuration.load_config(guild.id)
    await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('JOIN')} A new guild came up: {Utils.clean(guild.name)} ({guild.id}).", embed=Utils.server_info(guild))

async def on_guild_remove(guild):
    GearbotLogging.info(f"I was removed from a guild: {guild.name} ({guild.id}).")
    await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('LEAVE')} I was removed from a guild: {guild.name} ({guild.id}).", embed=Utils.server_info(guild))

class PostParseError(commands.BadArgument):

    def __init__(self, type, error):
        super().__init__(None)
        self.type = type
        self.error=error


async def on_command_error(bot, ctx: commands.Context, error):
    if isinstance(error, commands.BotMissingPermissions):
        GearbotLogging.error(f"Encountered a permission error while executing {ctx.command}: {error}")
        await ctx.send(error)
    elif isinstance(error, commands.CheckFailure):
        if ctx.command.qualified_name is not "latest" and ctx.guild is not None and Configuration.get_var(ctx.guild.id, "PERM_DENIED_MESSAGE"):
            await MessageUtils.send_to(ctx, 'LOCK', 'permission_denied')
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(error)
    elif isinstance(error, commands.MissingRequiredArgument):
        param = list(ctx.command.params.values())[min(len(ctx.args) + len(ctx.kwargs), len(ctx.command.params))]
        await ctx.send(
            f"{Emoji.get_chat_emoji('NO')} {Translator.translate('missing_arg', ctx, arg=param._name, error=error)}\n{Emoji.get_chat_emoji('WRENCH')} {Translator.translate('command_usage', ctx, usage=ctx.prefix.replace(ctx.me.mention, f'@{ctx.me.name}') + ctx.command.signature)}")
    elif isinstance(error, PostParseError):
        await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('bad_argument', ctx, type=error.type, error=error.error)}\n{Emoji.get_chat_emoji('WRENCH')} {Translator.translate('command_usage', ctx, usage=ctx.prefix.replace(ctx.me.mention, f'@{ctx.me.name}') + ctx.command.signature)}")
    elif isinstance(error, commands.BadArgument):
        param = list(ctx.command.params.values())[min(len(ctx.args) + len(ctx.kwargs), len(ctx.command.params))]
        await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('bad_argument', ctx, type=param._name, error=error)}\n{Emoji.get_chat_emoji('WRENCH')} {Translator.translate('command_usage', ctx, usage=ctx.prefix.replace(ctx.me.mention, f'@{ctx.me.name}') + ctx.command.signature)}")
    elif isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, PeeweeException):
        await handle_database_error(bot)

    else:
        await handle_exception("Command execution failed", bot, error.original, ctx=ctx)
        # notify caller
        e = Emoji.get_chat_emoji('BUG')
        await ctx.send(f"{e} Something went wrong while executing that command {e}")



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
    bot.errors = bot.errors + 1
    with sentry_sdk.push_scope() as scope:

        embed = Embed(colour=Colour(0xff0000), timestamp=datetime.utcfromtimestamp(time.time()))

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


        if isinstance(exception, PeeweeException):
            await handle_database_error(bot)

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