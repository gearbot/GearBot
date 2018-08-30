import asyncio
import datetime
import json
import os
import signal
import sys
import time
import traceback

import aiohttp
import discord
from discord.ext import commands
from peewee import PeeweeException

import Util
from Util import Configuration, Emoji, Utils, Translator, GearbotLogging, DocUtils
from database import DatabaseConnector

extensions = [
    "Basic",
    "Admin",
    "Moderation",
    "Serveradmin",
    "ModLog",
    "CustCommands",
    "BCVersionChecker",
    "Reload",
    "PageHandler",
    "Censor",
    "Infractions",
    "Minecraft",
    "DMMessages"
]

def prefix_callable(bot, message):
    user_id = bot.user.id
    prefixes = [f'<@!{user_id}> ', f'<@{user_id}> '] #execute commands by mentioning
    if message.guild is None or not bot.STARTUP_COMPLETE:
        prefixes.append('!') #use default ! prefix in DMs
    else:
        prefixes.append(Configuration.getConfigVar(message.guild.id, "PREFIX"))
    return prefixes


async def on_ready(bot):
    if not bot.STARTUP_COMPLETE:
        await GearbotLogging.onReady(bot, Configuration.getMasterConfigVar("BOT_LOG_CHANNEL"))
        info = await bot.application_info()
        await GearbotLogging.logToBotlog(message="Spinning up the gears!")
        await Util.readyBot(bot)
        Emoji.on_ready(bot)
        Utils.on_ready(bot)
        Translator.on_ready(bot)
        bot.loop.create_task(keepDBalive(bot)) # ping DB every hour so it doesn't run off

        #shutdown handler for clean exit on linux
        try:
            for signame in ('SIGINT', 'SIGTERM'):
                asyncio.get_event_loop().add_signal_handler(getattr(signal, signame),
                                        lambda: asyncio.ensure_future(Utils.cleanExit(bot, signame)))
        except Exception:
            pass #doesn't work on windows

        bot.aiosession = aiohttp.ClientSession()
        bot.start_time = datetime.datetime.utcnow()
        GearbotLogging.info("Loading cogs...")
        for extension in extensions:
            try:
                bot.load_extension("Cogs." + extension)
            except Exception as e:
                GearbotLogging.exception(f"Failed to load extention {extension}", e)
        GearbotLogging.info("Cogs loaded")

        if Configuration.getMasterConfigVar("CROWDIN_KEY") is not None:
            bot.loop.create_task(translation_task(bot))

        await DocUtils.update_docs(bot)

        bot.STARTUP_COMPLETE = True
        await GearbotLogging.logToBotlog(message=f"All turning gears at full speed, {info.name} ready to go!")
    await bot.change_presence(activity=discord.Activity(type=3, name='the gears turn'))



async def keepDBalive(bot):
    while not bot.is_closed():
        bot.database_connection.connection().ping(True)
        await asyncio.sleep(3600)

async def translation_task(bot):
    while not bot.is_closed():
        try:
            await Translator.update()
        except Exception as ex:
            GearbotLogging.error("Something went wrong during translation updates")
            GearbotLogging.error(traceback.format_exc())
            embed = discord.Embed(colour=discord.Colour(0xff0000),
                                  timestamp=datetime.datetime.utcfromtimestamp(time.time()))
            embed.set_author(name="Something went wrong during translation updates")
            embed.add_field(name="Exception", value=str(ex))
            v = ""
            for line in traceback.format_exc().splitlines():
                if len(v) + len(line) >= 1024:
                    embed.add_field(name="Stacktrace", value=v)
                    v = ""
                v = f"{v}\n{line}"
            if len(v) > 0:
                embed.add_field(name="Stacktrace", value=v)
            await GearbotLogging.logToBotlog(embed=embed)

        try:
            await asyncio.sleep(6*60*60)
        except asyncio.CancelledError:
            pass # bot shutting down


async def on_message(bot, message:discord.Message):
    if message.author.bot:
        if message.author.id == bot.user.id:
            bot.self_messages += 1
        bot.bot_messages += 1
        return
    ctx: commands.Context = await bot.get_context(message)
    bot.user_messages += 1
    if ctx.command is not None:
        bot.commandCount = bot.commandCount + 1
        if isinstance(ctx.channel, discord.TextChannel) and not ctx.channel.permissions_for(ctx.channel.guild.me).send_messages:
            try:
                await ctx.author.send("Hey, you tried triggering a command in a channel I'm not allowed to send messages in. Please grant me permissions to reply and try again.")
            except discord.Forbidden:
                pass #closed DMs
        else:
            await bot.invoke(ctx)


async def on_guild_join(guild: discord.Guild):
    GearbotLogging.info(f"A new guild came up: {guild.name} ({guild.id}).")
    Configuration.loadConfig(guild.id)

async def on_guild_remove(guild: discord.Guild):
    GearbotLogging.info(f"i was removed from a guild: {guild.name} ({guild.id}).")

async def on_command_error(bot, ctx: commands.Context, error):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command cannot be used in private messages.")
    elif isinstance(error, commands.BotMissingPermissions):
        GearbotLogging.error(f"Encountered a permission error while executing {ctx.command}: {error}")
        await ctx.send(error)
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send("Sorry. This command is disabled and cannot be used.")
    elif isinstance(error, commands.CheckFailure):
        if ctx.command.qualified_name is not "latest" and ctx.guild is not None and Configuration.getConfigVar(ctx.guild.id, "PERM_DENIED_MESSAGE"):
            await ctx.send(":lock: You do not have the required permissions to run this command")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(error)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"You are missing a required argument! (See {ctx.prefix}help {ctx.command.qualified_name} for info on how to use this command).")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Invalid argument given! (See {ctx.prefix}help {ctx.command.qualified_name} for info on how to use this commmand).")
    elif isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, PeeweeException):
        await handle_database_error(bot)

    else:
        bot.errors = bot.errors + 1
        # log to logger first just in case botlog logging fails as well
        GearbotLogging.exception(f"Command execution failed:\n"
                                 f"    Command: {ctx.command}\n"
                                 f"    Message: {ctx.message.content}\n"
                                 f"    Channel: {'Private Message' if isinstance(ctx.channel, discord.abc.PrivateChannel) else ctx.channel.name}\n"
                                 f"    Sender: {ctx.author.name}#{ctx.author.discriminator}\n"
                                 f"    Exception: {error}", error.original)
        # notify caller
        await ctx.send(":rotating_light: Something went wrong while executing that command :rotating_light:")

        embed = discord.Embed(colour=discord.Colour(0xff0000),
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))

        embed.set_author(name="Command execution failed:")
        embed.add_field(name="Command", value=ctx.command)
        embed.add_field(name="Original message", value=Utils.trim_message(ctx.message.content, 1024))
        embed.add_field(name="Channel",
                        value='Private Message' if isinstance(ctx.channel, discord.abc.PrivateChannel) else f"{ctx.channel.name} ({ctx.channel.id})")
        embed.add_field(name="Sender", value=f"{ctx.author.name}#{ctx.author.discriminator}")
        embed.add_field(name="Exception", value=error.original)
        v = ""
        for line in traceback.format_tb(error.original.__traceback__):
            if len(v) + len(line) > 1024:
                embed.add_field(name="Stacktrace", value=v)
                v = ""
            v = f"{v}\n{line}"
        if len(v) > 0:
            embed.add_field(name="Stacktrace", value=v)
        await GearbotLogging.logToBotlog(embed=embed)


async def on_error(bot, event, *args, **kwargs):
    type, exception, info = sys.exc_info()
    if isinstance(exception, PeeweeException):
        await handle_database_error(bot)
    try:
        # something went wrong and it might have been in on_command_error, make sure we log to the log file first
        bot.errors = bot.errors + 1
        GearbotLogging.error(f"error in {event}\n{args}\n{kwargs}")
        embed = discord.Embed(colour=discord.Colour(0xff0000),
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))

        embed.set_author(name=f"Caught an error in {event}:")

        embed.add_field(name="args", value=str(args))
        embed.add_field(name="kwargs", value=str(kwargs))
        embed.add_field(name="cause message", value=traceback._cause_message)
        v = ""
        for line in traceback.format_exc():
            if len(v) + len(line) > 1024:
                embed.add_field(name="Stacktrace", value=v)
                v = ""
            v = f"{v}{line}"
        if len(v) > 0:
            embed.add_field(name="Stacktrace", value=v)
            # try logging to botlog, wrapped in an try catch as there is no higher lvl catching to prevent taking donwn the bot (and if we ended here it might have even been due to trying to log to botlog
        await GearbotLogging.logToBotlog(embed=embed)
    except Exception as ex:
        GearbotLogging.error(
            f"Failed to log to botlog, either Discord broke or something is seriously wrong!\n{ex}")
        GearbotLogging.error(traceback.format_exc())

async def handle_database_error(bot):
    GearbotLogging.error(traceback.format_exc())
    # database trouble, notify bot owner
    message = f"{Emoji.get_chat_emoji('WARNING')} Peewee exception caught! attempting to reconnect to the database!"
    await GearbotLogging.message_owner(bot, message)
    await GearbotLogging.logToBotlog(message)

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
                await GearbotLogging.logToBotlog(message)
                with open("stage_3.txt", "w") as file:
                    file.write("stage_3")
                os.kill(os.getpid(), 9)
            elif os.path.isfile('stage_1.txt'):
                with open("stage_2.txt", "w") as file:
                    file.write("stage_2")
                message = f"{Emoji.get_chat_emoji('NO')} Reconnecting and bot rebooting failed, escalating to VM reboot"
                await GearbotLogging.message_owner(bot, message)
                await GearbotLogging.logToBotlog(message)
                data = {'type': 'reboot'}
                async with aiohttp.ClientSession(headers={'Content-Type': 'application/json',
                                                          'Authorization': f'Bearer {Configuration.getMasterConfigVar("DO_TOKEN")}'}) as session:
                    await session.post(f'https://api.digitalocean.com/v2/droplets/{Configuration.getMasterConfigVar("DO_ID")}/actions',
                                            data=json.dumps(data), timeout=30)
                time.sleep(60)

            else:
                message = f"{Emoji.get_chat_emoji('NO')} Reconnecting failed, escalating to reboot"
                await GearbotLogging.message_owner(bot, message)
                await GearbotLogging.logToBotlog(message)
                with open("stage_1.txt", "w") as file:
                    file.write("stage_1")
                os.kill(os.getpid(), 9)
        else:
            message = f"{Emoji.get_chat_emoji('YES')} 2nd reconnection attempt successfully connected!"
            await GearbotLogging.message_owner(bot, message)
            await GearbotLogging.logToBotlog(message)
    else:
        message = f"{Emoji.get_chat_emoji('YES')} 1st reconnection attempt successfully connected!"
        await GearbotLogging.message_owner(bot, message)
        await GearbotLogging.logToBotlog(message)