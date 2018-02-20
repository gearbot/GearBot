import datetime
import logging
import os
import time
import traceback
from argparse import ArgumentParser

import discord
from discord import abc
from discord.ext import commands

import Variables
from Util import GearbotLogging
from Util import configuration

configuration.loadGlobalConfig()
bot = commands.Bot(command_prefix=configuration.getMasterConfigVar("PREFIX", "!"))


@bot.event
async def on_ready():
    if not Variables.STARTUP_COMPLETE:
        # GearbotLogging.info('Logged on as {0}!'.format(bot.user))
        await GearbotLogging.onReady(bot)
        await configuration.onReady(bot)
        Variables.STARTUP_COMPLETE = True


@bot.event
async def on_message(message):
    # GearBotLogging.info('Message from {0.author}: {0.content}'.format(message))
    await bot.process_commands(message)


@bot.event
async def on_guild_join(guild: discord.Guild):
    GearbotLogging.info(f"A new guild came up: {guild.name} ({guild.id})")


@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CheckFailure):
        # just a random user trying something he's not allowed to do
        await ctx.send(":lock: You do not have the required permissions to run this command")
    elif isinstance(error, discord.Forbidden):
        # permission misconfigurations
        GearbotLogging.error(f"Encountered a permissions error while executing {ctx.command}")
        await ctx.send("Something does not seem to be configured right, i do not have all the permissions required by this command")
    elif isinstance(error, commands.TooManyArguments):
        await ctx.send("More arguments where supplied then i know how to handle")
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send("This command is dissabled")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("This command does not work in private messages")
    elif isinstance(error, commands.MissingRequiredArgument)\
            or isinstance(error, commands.BadArgument)\
            or isinstance(error, commands.CommandOnCooldown)\
            or isinstance(error, commands.MissingPermissions)\
            or isinstance(error, commands.BotMissingPermissions):
        await ctx.send(error)

    else:
        # log to logger first just in case botlog logging fails as well
        GearbotLogging.exception(f"Command execution failed:"
                                 f"    Command: {ctx.command}"
                                 f"    Message: {ctx.message.content}"
                                 f"    Channel: {'Private Message' if isinstance(ctx.channel, abc.PrivateChannel) else ctx.channel.name}"
                                 f"    Sender: {ctx.author.name}#{ctx.author.discriminator}"
                                 f"    Exception: {error}", error)
        #notify caller
        await ctx.send(":rotating_light: Something went wrong while executing that command :rotating_light:")

        embed = discord.Embed(colour=discord.Colour(0xff0000),
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))

        embed.set_author(name="Command execution failed:")
        embed.add_field(name="Command", value=ctx.command)
        embed.add_field(name="Original message", value=ctx.message.content)
        embed.add_field(name="Channel", value='Private Message' if isinstance(ctx.channel, abc.PrivateChannel) else ctx.channel.name)
        embed.add_field(name="Sender", value=f"{ctx.author.name}#{ctx.author.discriminator}")
        embed.add_field(name="Exception", value=error)
        v = ""
        for line in traceback.format_tb(error.__traceback__):
            v = f"{v}\n{line}"
        embed.add_field(name="Stacktrace", value=v)
        await GearbotLogging.logToBotlog(embed=embed)


@bot.event
async def on_error(event, *args, **kwargs):
    #something went wrong and it might have been in on_command_error, make sure we log to the log file first
    GearbotLogging.error(f"error in {event}\n{args}\n{kwargs}")
    embed = discord.Embed(colour=discord.Colour(0xff0000),
                          timestamp=datetime.datetime.utcfromtimestamp(time.time()))

    embed.set_author(name=f"Caught an error in {event}:")

    embed.add_field(name="args", value=str(args))
    embed.add_field(name="kwargs", value=str(kwargs))
    embed.add_field(name="Stacktrace", value=traceback.format_exc())
    await GearbotLogging.logToBotlog(embed=embed)
    #try logging to botlog, wrapped in an try catch as there is no higher lvl catching to prevent taking donwn the bot (and if we ended here it might have even been due to trying to log to botlog
    try:
        pass
    except Exception as ex:
        GearbotLogging.exception(f"Failed to log to botlog, eighter discord broke or something is seriously wrong!\n{ex}")



extensions = [
    "Basic",
    "Admin"
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
    elif not configuration.getMasterConfigVar("LOGIN_TOKEN", "0") is "0":
        token = configuration.getMasterConfigVar("LOGIN_TOKEN")
    else:
        token = input("Please enter your Discord token: ")
    for extension in extensions:
        try:
            bot.load_extension("Cogs." + extension)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            print('Failed to load extension {}\n{}'.format(extension, exc))
    bot.run(token)
