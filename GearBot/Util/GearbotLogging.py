import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

import discord
from discord.ext import commands

from Util import Configuration, GlobalHandlers

LOGGER = logging.getLogger('gearbot')
DISCORD_LOGGER = logging.getLogger('discord')

BOT_LOG_CHANNEL: discord.TextChannel
STARTUP_ERRORS = []
BOT: commands.AutoShardedBot = None
LOG_CACHE = dict()
SHOULD_TERMINATE = False


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

    handler = TimedRotatingFileHandler(filename='logs/discord.log', encoding='utf-8', when="h", interval=4,
                                       backupCount=30)
    DISCORD_LOGGER.addHandler(handler)


async def onReady(bot: commands.Bot, channelID):
    global BOT_LOG_CHANNEL, BOT, STARTUP_ERRORS
    BOT = bot
    BOT_LOG_CHANNEL = bot.get_channel(int(channelID))
    if BOT_LOG_CHANNEL is None:
        LOGGER.error(
            "==========================Logging channel is misconfigured, aborting startup!==========================")
        await bot.logout()

    if len(STARTUP_ERRORS) > 0:
        await bot_log(
            f":rotating_light: Caught {len(STARTUP_ERRORS)} {'exceptions' if len(STARTUP_ERRORS) > 1 else 'exception'} during startup.")
        for e in STARTUP_ERRORS:
            await e
        STARTUP_ERRORS = []

    bot.loop.create_task(log_pump())


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


async def bot_log(message=None, embed=None):
    if BOT_LOG_CHANNEL is not None:
        return await BOT_LOG_CHANNEL.send(content=message, embed=embed)
    else:
        STARTUP_ERRORS.append(bot_log(message, embed))


def log_to(guild_id, type, message=None, embed=None, file=None):
    channels = Configuration.get_var(guild_id, "LOG_CHANNELS")
    for cid, info in channels.items():
        if type in info:
            if Configuration.get_var(guild_id, "TIMESTAMPS"):
                message = f"[`{datetime.strftime(datetime.now(), '%H:%M:%S')}`] {message}"
            if cid not in LOG_CACHE:
                LOG_CACHE[cid] = []
            LOG_CACHE[cid].append((message, embed, file))

async def log_pump():
    info("Starting log pump")
    empty = []
    senders = []
    embed = file = cid = todo = to_send = None
    while not SHOULD_TERMINATE:
        try:
            embed = file = None
            for cid, todo in LOG_CACHE.items():
                channel = BOT.get_channel(int(cid))
                if channel is not None and len(todo) > 0:
                    permissions = channel.permissions_for(channel.guild.me)
                    to_send = ""
                    while len(todo) > 0:
                        message, embed, file = todo[0]
                        if (not permissions.send_messages) or (embed is not None and not permissions.embed_links) or (
                                file is not None and not permissions.attach_files):
                            todo.pop(0)
                            continue
                        elif len(to_send) + len(message) < 1999:
                            to_send += f"{message}\n"
                            todo.pop(0)
                        else:
                            break
                        if embed is not None or file is not None:
                            break
                    senders.append(channel.send(to_send, embed=embed, file=file))
                else:
                    empty.append(cid)
            for e in empty:
                del LOG_CACHE[e]
            empty = []
            for s in senders:
                await s
            senders = []
            await asyncio.sleep(0.1)
        except Exception as e:
            await GlobalHandlers.handle_exception("LOG PUMP", BOT, e, kwargs=dict(cid=cid, todo=todo, to_send=to_send, LOG_CACHE=LOG_CACHE, embed=embed, file=file, empty=empty))
    info("Log pump terminated")




async def message_owner(bot, message):
    if bot.owner_id is None:
        app = await bot.application_info()
        bot.owner_id = app.owner.id
    owner = bot.get_user(bot.owner_id)
    dm_channel = owner.dm_channel
    if dm_channel is None:
        await owner.create_dm()
    await owner.dm_channel.send(message)
