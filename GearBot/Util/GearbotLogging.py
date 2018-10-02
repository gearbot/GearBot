import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

import discord
from discord.ext import commands

from Util import Configuration, GlobalHandlers, Utils, Translator, Emoji

LOGGER = logging.getLogger('gearbot')
DISCORD_LOGGER = logging.getLogger('discord')

BOT_LOG_CHANNEL: discord.TextChannel
STARTUP_ERRORS = []
BOT: commands.AutoShardedBot = None
LOG_PUMP = None
LOG_ERRORS = 0


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
    global BOT_LOG_CHANNEL, BOT, STARTUP_ERRORS, LOG_PUMP
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

def initialize_pump(bot):
    global LOG_PUMP
    LOG_PUMP = LogPump(bot)
    bot.loop.create_task(LOG_PUMP.pump())


def debug(message):
    LOGGER.debug(message)


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


def log_to(guild_id, type, message=None, embed=None, file=None, can_stamp=True, cleaner=None, tag_on=None):
    remaining = None
    if message is None and embed is None and file is None:
        raise ValueError("What the heck is trying to log nothing?")
    if can_stamp and Configuration.get_var(guild_id, "TIMESTAMPS"):
        stamp = f"[`{datetime.strftime(datetime.now(), '%H:%M:%S')}`]"
        if message is None:
            message = stamp
        else:
            message = f"{stamp} {Utils.trim_message(message, 1985)}"
    if tag_on is not None:
        if message is None:
            message = tag_on
        else:
            if len(message) + len(tag_on) < 1999:
                message = f"{message} {tag_on}"
            else:
                remaining = tag_on
    message = Utils.trim_message(f"{message}\u200b", 1999)
    channels = Configuration.get_var(guild_id, "LOG_CHANNELS")
    for cid, info in channels.items():
        if type in info:
            if remaining is None:
                LOG_PUMP.receive(cid, (message, embed, file, cleaner))
            else:
                LOG_PUMP.receive(cid, (message, None, None, None))
                LOG_PUMP.receive(cid, (tag_on, embed, file, cleaner))



async def send_to(destination, emoji, message, delete_after=None, translate=True, **kwargs):
    translated = Translator.translate(message, destination.guild, **kwargs) if translate else message
    return await destination.send(f"{Emoji.get_chat_emoji(emoji)} {translated}", delete_after=delete_after)

async def message_owner(bot, message):
    if bot.owner_id is None:
        app = await bot.application_info()
        bot.owner_id = app.owner.id
    owner = bot.get_user(bot.owner_id)
    dm_channel = owner.dm_channel
    if dm_channel is None:
        await owner.create_dm()
    await owner.dm_channel.send(message)


class LogPump:

    def __init__(self, bot):
        self.todo = dict()
        self.running = True
        self.bot = bot
        self.NUKED = False
        info("Starting log pump")

    async def pump(self):
        info("Log pump engaged")
        empty = []
        embed = file = cid = todo = to_send = None
        while (self.running or len(self.todo) > 0) and not self.NUKED:
            try:
                cleaners = []
                empty = []
                senders = []
                embed = file = None
                for cid, todo in self.todo.items():
                    channel = BOT.get_channel(int(cid))
                    if channel is not None and len(todo) > 0:
                        permissions = channel.permissions_for(channel.guild.me)
                        to_send = ""
                        while len(todo) > 0:
                            message, embed, file, cleaner = todo[0]
                            if message is None or message.strip() == "":
                                message = ""
                            if (not permissions.send_messages) or (
                                    embed is not None and not permissions.embed_links) or (
                                    file is not None and not permissions.attach_files):
                                todo.pop(0)
                                cleaners.append(cleaner)
                                continue
                            elif len(to_send) + len(message) < 1999:
                                to_send += f"{message}\n"
                                todo.pop(0)
                            else:
                                break
                            if embed is not None or file is not None:
                                break
                        try:
                            senders.append(channel.send(to_send if to_send != "" else None, embed=embed, file=file))
                        except Exception as e:
                            await GlobalHandlers.handle_exception("LOG PUMP", BOT, e,
                                                                  kwargs=dict(cid=cid, todo=todo, to_send=to_send,
                                                                              LOG_CACHE=self.todo, embed=embed,
                                                                              file=file,
                                                                              empty=empty))
                    else:
                        empty.append(cid)
                for e in empty:
                    del self.todo[e]
                for s in senders:
                    try:
                        await s
                    except Exception as e:
                        await log_error()
                        await GlobalHandlers.handle_exception("LOG PUMP", BOT, e,
                                                              kwargs=dict(cid=cid, todo=todo, to_send=to_send,
                                                                          LOG_CACHE=self.todo, embed=embed, file=file,
                                                                          empty=empty))
                for c in cleaners:
                    c()
                await asyncio.sleep(0.1)
            except Exception as e:
                await log_error()
                await GlobalHandlers.handle_exception("LOG PUMP", BOT, e,
                                                      kwargs=dict(cid=cid, todo=todo, to_send=to_send,
                                                                  LOG_CACHE=self.todo, embed=embed, file=file,
                                                                  empty=empty))
        info("Log pump terminated")

    def receive(self, cid, data):
        if cid not in self.todo:
            self.todo[cid] = []
        self.todo[cid].append(data)


async def log_error():
    global LOG_ERRORS, LOG_PUMP
    LOG_ERRORS += 1
    if LOG_ERRORS >= 10:
        LOG_ERRORS = 0
        error("=========Log pump error limit reached, deploying nuke to unclog the system=========")
        LOG_PUMP.NUKED = True
        initialize_pump(BOT)
        await bot_log("Log pump got clogged, nuked and restarted, moving on")

