import asyncio
import datetime
import json
import logging
import os
import signal
import sys
import time
import traceback
from argparse import ArgumentParser
from asyncio import CancelledError

import aiohttp
import discord
from discord import abc
from discord.ext import commands
from peewee import PeeweeException

import Util
from Util import Configuration, GearbotLogging, Emoji, Translator, DocUtils
from Util import Utils as Utils
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
    "Minecraft"
]

def prefix_callable(bot, message):
    user_id = bot.user.id
    prefixes = [f'<@!{user_id}> ', f'<@{user_id}> '] #execute commands by mentioning
    if message.guild is None or not bot.STARTUP_COMPLETE:
        prefixes.append('!') #use default ! prefix in DMs
    else:
        prefixes.append(Configuration.getConfigVar(message.guild.id, "PREFIX"))
    return prefixes

bot = commands.AutoShardedBot(command_prefix=prefix_callable, case_insensitive=True)
bot.STARTUP_COMPLETE = False
bot.messageCount = 0
bot.commandCount = 0
bot.errors = 0
bot.database_errors = 0

@bot.event
async def on_ready():
    if not bot.STARTUP_COMPLETE:
        await Util.readyBot(bot)
        Emoji.on_ready(bot)
        Utils.on_ready(bot)
        Translator.on_ready(bot)
        bot.loop.create_task(keepDBalive()) # ping DB every hour so it doesn't run off

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
            bot.loop.create_task(translation_task())

        await DocUtils.update_docs(bot)

        bot.STARTUP_COMPLETE = True
    await bot.change_presence(activity=discord.Activity(type=3, name='the gears turn'))

async def translation_task():
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
        except CancelledError:
            pass # bot shutting down

async def keepDBalive():
    while not bot.is_closed():
        bot.database_connection.connection().ping(True)
        await asyncio.sleep(3600)

@bot.event
async def on_message(message:discord.Message):
    if message.author.bot:
        return
    bot.messageCount = bot.messageCount + 1
    ctx:commands.Context = await bot.get_context(message)
    if ctx.command is not None:
        bot.commandCount = bot.commandCount + 1
        if isinstance(ctx.channel, discord.TextChannel) and not ctx.channel.permissions_for(ctx.channel.guild.me).send_messages:
            try:
                await ctx.author.send("Hey, you tried triggering a command in a channel I'm not allowed to send messages in. Please grant me permissions to reply and try again.")
            except discord.Forbidden:
                pass #closed DMs
        else:
            await bot.invoke(ctx)


@bot.event
async def on_guild_join(guild: discord.Guild):
    GearbotLogging.info(f"A new guild came up: {guild.name} ({guild.id}).")
    Configuration.loadConfig(guild.id)


@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command cannot be used in private messages.")
    elif isinstance(error, commands.BotMissingPermissions):
        GearbotLogging.error(f"Encountered a permission error while executing {ctx.command}.")
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
        await handle_database_error()

    else:
        bot.errors = bot.errors + 1
        # log to logger first just in case botlog logging fails as well
        GearbotLogging.exception(f"Command execution failed:\n"
                                 f"    Command: {ctx.command}\n"
                                 f"    Message: {ctx.message.content}\n"
                                 f"    Channel: {'Private Message' if isinstance(ctx.channel, abc.PrivateChannel) else ctx.channel.name}\n"
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
                        value='Private Message' if isinstance(ctx.channel, abc.PrivateChannel) else f"{ctx.channel.name} ({ctx.channel.id})")
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


@bot.event
async def on_error(event, *args, **kwargs):
    type, exception, info = sys.exc_info()
    if isinstance(exception, PeeweeException):
        await handle_database_error()
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

async def handle_database_error():
    GearbotLogging.error(traceback.format_exc())
    # database trouble, notify bot owner
    message = f"{Emoji.get_chat_emoji('WARNING')} Peewee exception caught! attempting to reconnect to the database!"
    if bot.owner_id is None:
        app = await bot.application_info()
        bot.owner_id = app.owner.id
    owner =  bot.get_user(bot.owner_id)
    dmchannel = owner.dm_channel
    if dmchannel is None:
        await owner.create_dm()
    await owner.dm_channel.send(message)
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
                await bot.get_user(bot.owner_id).dm_channel.send(message)
                await GearbotLogging.logToBotlog(message)
                data = {'type': 'reboot'}
                async with aiohttp.ClientSession(headers={'Content-Type': 'application/json',
                                                          'Authorization': f'Bearer {Configuration.getMasterConfigVar("DO_TOKEN")}'}) as session:
                    await session.post(f'https://api.digitalocean.com/v2/droplets/{Configuration.getMasterConfigVar("DO_ID")}/actions',
                                            data=json.dumps(data), timeout=30)
                time.sleep(60)

            else:
                message = f"{Emoji.get_chat_emoji('NO')} Reconnecting failed, escalating to reboot"
                await bot.get_user(bot.owner_id).dm_channel.send(message)
                await GearbotLogging.logToBotlog(message)
                with open("stage_1.txt", "w") as file:
                    file.write("stage_1")
                os.kill(os.getpid(), 9)
        else:
            message = f"{Emoji.get_chat_emoji('YES')} 2nd reconnection attempt successfully connected!"
            await bot.get_user(bot.owner_id).dm_channel.send(message)
            await GearbotLogging.logToBotlog(message)
    else:
        message = f"{Emoji.get_chat_emoji('YES')} 1st reconnection attempt successfully connected!"
        await bot.get_user(bot.owner_id).dm_channel.send(message)
        await GearbotLogging.logToBotlog(message)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--debug", help="Runs the bot in debug mode", dest='debug', action='store_true')
    parser.add_argument("--debugLogging", help="Set debug logging level", action='store_true')
    parser.add_argument("--token", help="Specify your Discord token")

    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w+')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    GearbotLogging.init_logger()

    clargs = parser.parse_args()
    if 'gearbotlogin' in os.environ:
        token = os.environ['gearbotlogin']
    elif clargs.token:
        token = clargs.token
    elif not Configuration.getMasterConfigVar("LOGIN_TOKEN", "0") is "0":
        token = Configuration.getMasterConfigVar("LOGIN_TOKEN")
    else:
        token = input("Please enter your Discord token: ")
    bot.remove_command("help")
    Util.prepDatabase(bot)
    GearbotLogging.info("Ready to go, spinning up the gears")
    bot.run(token)
    GearbotLogging.info("GearBot shutting down, cleaning up")
    bot.database_connection.close()
    GearbotLogging.info("Cleanup complete")

