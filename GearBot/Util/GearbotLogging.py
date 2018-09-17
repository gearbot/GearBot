import logging
import os
import sys
import traceback
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

import discord
from discord.ext import commands

from Util import Configuration

LOGGER = logging.getLogger('gearbot')
DISCORD_LOGGER = logging.getLogger('discord')


BOT_LOG_CHANNEL:discord.TextChannel
STARTUP_ERRORS = []
BOT:commands.AutoShardedBot = None


def init_logger():
    LOGGER.setLevel(logging.DEBUG)
    DISCORD_LOGGER.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    DISCORD_LOGGER.addHandler(handler)

    if not os.path.isdir("logs"):
        os.mkdir("logs")
    handler = TimedRotatingFileHandler(filename='logs/gearbot.log', encoding='utf-8', when="midnight", backupCount=30)
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    DISCORD_LOGGER.addHandler(handler)
    LOGGER.addHandler(handler)


    handler = TimedRotatingFileHandler(filename='logs/discord.log', encoding='utf-8', when="midnight", backupCount=7)
    DISCORD_LOGGER.addHandler(handler)


async def onReady(bot:commands.Bot, channelID):
    global BOT_LOG_CHANNEL, BOT
    BOT = bot
    BOT_LOG_CHANNEL = bot.get_channel(int(channelID))
    if BOT_LOG_CHANNEL is None:
        LOGGER.error("==========================Logging channel is misconfigured, aborting startup!==========================")
        await bot.logout()

    if len(STARTUP_ERRORS) > 0:
        await bot_log(
            f":rotating_light: Caught {len(STARTUP_ERRORS)} {'exceptions' if len(STARTUP_ERRORS) > 1 else 'exception'} during startup.")
        for e in STARTUP_ERRORS:
            await e


def info(message):
    LOGGER.info(message)


def warn(message):
    LOGGER.warning(message)


def error(message):
    LOGGER.error(message)

def exception(message, error):
    LOGGER.error(message)
    trace = ""
    LOGGER.error(str(error))
    for line in traceback.format_tb(error.__traceback__):
        trace = f"{trace}\n{line}"
    LOGGER.error(trace)


async def bot_log(message = None, embed = None):
    if BOT_LOG_CHANNEL is not None:
        return await BOT_LOG_CHANNEL.send(content=message, embed=embed)
    else:
        STARTUP_ERRORS.append(bot_log(message, embed))

async def log_to(guild_id, type, message=None, embed=None, file=None):
    channels = Configuration.get_var(guild_id, "LOG_CHANNELS")
    for cid, info in channels.items():
        if info["EVERYTHING"] or type in info["TYPES"]:
            channel = BOT.get_channel(int(cid))
            if channel is not None:
                permissions = channel.permissions_for(BOT.get_guild(guild_id).me)
                if permissions.send_messages and (embed is None or permissions.embed_links) and (file is None or permissions.attach_files):
                    if Configuration.get_var(guild_id, "TIMESTAMPS"):
                        message = f"[{datetime.strftime(datetime.now(), '%H:%M:%S')}] {message}"
                    await channel.send(message, embed=embed, file=file)

async def message_owner(bot, message):
    if bot.owner_id is None:
        app = await bot.application_info()
        bot.owner_id = app.owner.id
    owner =  bot.get_user(bot.owner_id)
    dm_channel = owner.dm_channel
    if dm_channel is None:
        await owner.create_dm()
    await owner.dm_channel.send(message)