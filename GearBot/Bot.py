import datetime
import logging
import os
import time
import traceback
from argparse import ArgumentParser

import discord
from discord import abc
from discord.ext import commands
from peewee import MySQLDatabase

from Util import Configuration
from Util import GearbotLogging

#load global config before database
Configuration.loadGlobalConfig()

from database import DatabaseConnector

def prefix_callable(bot, message):
    user_id = bot.user.id
    prefixes = [f'<@!{user_id}> ', f'<@{user_id}> '] #execute commands by mentioning
    if message.guild is None:
        prefixes.append('!') #use default ! prefix in DMs
    else:
        prefixes.append(Configuration.getConfigVar(message.guild.id, "PREFIX"))
    return prefixes

bot = commands.Bot(command_prefix=prefix_callable)
bot.STARTUP_COMPLETE = False

@bot.event
async def on_ready():
    if not bot.STARTUP_COMPLETE:
        await Configuration.onReady(bot)
        await GearbotLogging.onReady(bot, Configuration.MASTER_CONFIG["BOT_LOG_CHANNEL"])
        bot.STARTUP_COMPLETE = True


@bot.event
async def on_message(message:discord.Message):
    if message.channel.id == 414716941131841549:
        positive = None
        positiveID = 0
        negative = None
        negativeID = 0
        for emoji in message.guild.emoji:
            if emoji.id == positiveID:
                positive = emoji
            elif emoji.id == negativeID:
                negative = emoji

        await message.add_reaction(positive)
        await message.add_reaction(negative)
    # GearBotLogging.info('Message from {0.author}: {0.content}'.format(message))
    await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(emoji:discord.PartialEmoji, message_id, channel_id, user_id):
    message:discord.Message = await bot.get_channel(channel_id).get_message(message_id)

@bot.event
async def on_guild_join(guild: discord.Guild):
    GearbotLogging.info(f"A new guild came up: {guild.name} ({guild.id})")


@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command cannot be used in private messages.")
    elif isinstance(error, commands.BotMissingPermissions):
        GearbotLogging.error(f"Encountered a permissions error while executing {ctx.command}")
        await ctx.send(error)
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send("Sorry. This command is disabled and cannot be used.")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(":lock: You do not have the required permissions to run this command")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(error)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"You are missing a required argument!(See !help {ctx.command.qualified_name} for info on how to use this command)")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Invalid argument given! (See !help {ctx.command.qualified_name} for info on how to use this commmand)")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
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
        embed.add_field(name="Original message", value=ctx.message.content)
        embed.add_field(name="Channel",
                        value='Private Message' if isinstance(ctx.channel, abc.PrivateChannel) else ctx.channel.name)
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
    # something went wrong and it might have been in on_command_error, make sure we log to the log file first
    GearbotLogging.error(f"error in {event}\n{args}\n{kwargs}")
    embed = discord.Embed(colour=discord.Colour(0xff0000),
                          timestamp=datetime.datetime.utcfromtimestamp(time.time()))

    embed.set_author(name=f"Caught an error in {event}:")

    embed.add_field(name="args", value=str(args))
    embed.add_field(name="kwargs", value=str(kwargs))
    v = ""
    for line in traceback.format_exc():
        if len(v) + len(line) > 1024:
            embed.add_field(name="Stacktrace", value=v)
            v = ""
        v = f"{v}{line}"
    if len(v) > 0:
        embed.add_field(name="Stacktrace", value=v)
    await GearbotLogging.logToBotlog(embed=embed)
    # try logging to botlog, wrapped in an try catch as there is no higher lvl catching to prevent taking donwn the bot (and if we ended here it might have even been due to trying to log to botlog
    try:
        pass
    except Exception as ex:
        GearbotLogging.error(
            f"Failed to log to botlog, eighter discord broke or something is seriously wrong!\n{ex}")
        GearbotLogging.error(traceback.format_exc())


extensions = [
    "Basic",
    "Admin",
    "Moderation",
    "Serveradmin",
    "ModLog",
    "CustCommands"
]

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--debug", help="Runs the bot in debug mode", dest='debug', action='store_true')
    parser.add_argument("--debugLogging", help="Set debug logging level", action='store_true')
    parser.add_argument("--token", help="Specify your Discord token")

    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)
    clargs = parser.parse_args()
    if 'gearbotlogin' in os.environ:
        token = os.environ['gearbotlogin']
    elif clargs.token:
        token = clargs.token
    elif not Configuration.getMasterConfigVar("LOGIN_TOKEN", "0") is "0":
        token = Configuration.getMasterConfigVar("LOGIN_TOKEN")
    else:
        token = input("Please enter your Discord token: ")
    for extension in extensions:
        try:
            bot.load_extension("Cogs." + extension)
        except Exception as e:
            GearbotLogging.startupError(f"Failed to load extention {extension}", e)
    GearbotLogging.info("Connecting to the database")
    DatabaseConnector.init()
    bot.database_connection: MySQLDatabase = DatabaseConnector.connection
    GearbotLogging.info("Database connection established, spinning up")
    bot.run(token)
    bot.database_connection.close()
