import logging
import os
from argparse import ArgumentParser

import discord
from discord.ext import commands

import Util
from Util import Configuration, GearbotLogging, GlobalHandlers


def prefix_callable(bot, message):
    return GlobalHandlers.prefix_callable(bot, message)

bot = commands.AutoShardedBot(command_prefix=prefix_callable, case_insensitive=True)
bot.STARTUP_COMPLETE = False
bot.user_messages = 0
bot.bot_messages = 0
bot.self_messages = 0
bot.commandCount = 0
bot.custom_command_count = 0
bot.errors = 0
bot.eaten = 0
bot.database_errors = 0

@bot.event
async def on_ready():
    await GlobalHandlers.on_ready(bot)

@bot.event
async def on_message(message:discord.Message):
    await GlobalHandlers.on_message(bot, message)


@bot.event
async def on_guild_join(guild: discord.Guild):
    await GlobalHandlers.on_guild_join(guild)

@bot.event
async def on_guild_remove(guild: discord.Guild):
    await GlobalHandlers.on_guild_remove(guild)

@bot.event
async def on_command_error(ctx: commands.Context, error):
    await GlobalHandlers.on_command_error(bot, ctx, error)


@bot.event
async def on_error(event, *args, **kwargs):
    await GlobalHandlers.on_error(bot, event, *args, **kwargs)

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

