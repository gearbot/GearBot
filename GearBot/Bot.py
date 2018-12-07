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
bot.hot_reloading = False

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
    parser.add_argument("--token", help="Specify your Discord token")

    GearbotLogging.init_logger()

    clargs = parser.parse_args()
    if 'gearbotlogin' in os.environ:
        token = os.environ['gearbotlogin']
    elif clargs.token:
        token = clargs.token
    elif not Configuration.get_master_var("LOGIN_TOKEN", "0") is "0":
        token = Configuration.get_master_var("LOGIN_TOKEN")
    else:
        token = input("Please enter your Discord token: ")
    bot.remove_command("help")
    Util.prepDatabase(bot)
    GearbotLogging.info("Ready to go, spinning up the gears")
    bot.run(token)
    GearbotLogging.info("GearBot shutting down, cleaning up")
    bot.database_connection.close()
    GearbotLogging.info("Cleanup complete")

