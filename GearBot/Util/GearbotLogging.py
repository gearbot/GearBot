import logging
import sys
import traceback

import discord
from discord.ext import commands

from Util import configuration

logger = logging.getLogger('gearbot')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='gearbot.log', encoding='utf-8', mode='w+')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

BOT_LOG_CHANNEL:discord.TextChannel


def info(message):
    logger.info(message)


def warn(message):
    logger.warning(message)


def error(message):
    logger.error(message)

def exception(message, error):
    logger.error(message)
    traceback.format_tb(error.__traceback__)


async def onReady(client:commands.Bot):
    global BOT_LOG_CHANNEL
    BOT_LOG_CHANNEL = client.get_channel(configuration.getMasterConfigVar("BOT_LOG_CHANNEL", 0))
    if BOT_LOG_CHANNEL is None:
        logger.error("Logging channel is misconfigured, aborting startup")
        await client.logout()
    await logToBotlog(message="Gearbot startup sequence initialized, spinning up the gears")


async def logToBotlog(message = None, embed = None, log = True):
    await BOT_LOG_CHANNEL.send(content=message, embed=embed)
    if log:
        info(message)