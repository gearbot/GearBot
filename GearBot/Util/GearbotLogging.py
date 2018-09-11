import datetime
import logging
import os
import sys
import time
import traceback
from logging.handlers import TimedRotatingFileHandler

import discord
from discord.ext import commands

from Util import Configuration

logger = logging.getLogger('gearbot')
dlogger = logging.getLogger('discord')
def init_logger():
    logger.setLevel(logging.DEBUG)
    dlogger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    dlogger.addHandler(handler)

    if not os.path.isdir("logs"):
        os.mkdir("logs")
    handler = TimedRotatingFileHandler(filename='logs/gearbot.log', encoding='utf-8', when="midnight", backupCount=30)
    handler.setFormatter(formatter)
    dlogger.addHandler(handler)
    logger.addHandler(handler)

BOT_LOG_CHANNEL:discord.TextChannel

startupErrors = []


def info(message):
    logger.info(message)


def warn(message):
    logger.warning(message)


def error(message):
    logger.error(message)

def exception(message, error):
    logger.error(message)
    trace = ""
    logger.error(str(error))
    for line in traceback.format_tb(error.__traceback__):
        trace = f"{trace}\n{line}"
    logger.error(trace)


# for errors during startup before the bot fully loaded and can't log to botlog yet
def startupError(message, error):
    logger.exception(message)
    startupErrors.append({
        "message": message,
        "exception": error,
        "stacktrace": traceback.format_exc().splitlines()
    })



async def onReady(bot:commands.Bot, channelID):
    global BOT_LOG_CHANNEL
    BOT_LOG_CHANNEL = bot.get_channel(int(channelID))
    if BOT_LOG_CHANNEL is None:
        logger.error("Logging channel is misconfigured, aborting startup!")
        await bot.logout()

    if len(startupErrors) > 0:
        await logToBotlog(f":rotating_light: Caught {len(startupErrors)} {'exceptions' if len(startupErrors) > 1 else 'exception'} during startup.")
        for error in startupErrors:
            embed = discord.Embed(colour=discord.Colour(0xff0000),
                                  timestamp=datetime.datetime.utcfromtimestamp(time.time()))

            embed.set_author(name=error["message"])

            embed.add_field(name="Exception", value=error["exception"])
            stacktrace = ""
            while len(error["stacktrace"]) > 0:
                partial = error["stacktrace"].pop(0)
                if len(stacktrace) + len(partial) > 1024:
                    embed.add_field(name="Stacktrace", value=stacktrace)
                    stacktrace = ""
                stacktrace = f"{stacktrace}\n{partial}"
            if len(stacktrace) > 0:
                embed.add_field(name="Stacktrace", value=stacktrace)
            await logToBotlog(embed=embed)




async def logToBotlog(message = None, embed = None):
    return await BOT_LOG_CHANNEL.send(content=message, embed=embed)

async def logToModLog(guild, message=None, embed=None):
    modlog:discord.TextChannel = guild.get_channel(Configuration.getConfigVar(guild.id, "MOD_LOGS"))
    if modlog is not None:
        perms = modlog.permissions_for(guild.me)
        if perms.send_messages:
            await modlog.send(message, embed=embed)
        #TODO: notify guild owner?


async def log_to_minor_log(guild, message=None, embed=None, file=None):
    minor_log:discord.TextChannel = guild.get_channel(Configuration.getConfigVar(guild.id, "MINOR_LOGS"))
    if minor_log is not None:
        perms = minor_log.permissions_for(guild.me)
        if perms.send_messages:
            await minor_log.send(message, embed=embed, file=file)

async def message_owner(bot, message):
    if bot.owner_id is None:
        app = await bot.application_info()
        bot.owner_id = app.owner.id
    owner =  bot.get_user(bot.owner_id)
    dm_channel = owner.dm_channel
    if dm_channel is None:
        await owner.create_dm()
    await owner.dm_channel.send(message)