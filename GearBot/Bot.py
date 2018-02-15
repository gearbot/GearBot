import logging
import os
from argparse import ArgumentParser
import traceback

import discord
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
    #GearBotLogging.info('Message from {0.author}: {0.content}'.format(message))
    await bot.process_commands(message)


@bot.event
async def on_guild_join(guild:discord.Guild):
    GearbotLogging.info(f"A new guild came up: {guild.name} ({guild.id})")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        GearbotLogging.warn("a command was not allowed to run")

@bot.event
async def on_error(event, *args, **kwargs):
    GearbotLogging.error(f"error in {event}")


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
