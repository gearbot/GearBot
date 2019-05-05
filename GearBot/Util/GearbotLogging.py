import asyncio
import logging
import os
import sys
import traceback
from collections import namedtuple
from concurrent.futures import CancelledError
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

import discord
import pytz
import sentry_sdk
from aiohttp import ClientOSError, ServerDisconnectedError
from discord import ConnectionClosed
from discord.ext import commands

from Bot import TheRealGearBot
from Util import Configuration, Utils, MessageUtils

LOGGER = logging.getLogger('gearbot')
DISCORD_LOGGER = logging.getLogger('discord')

BOT_LOG_CHANNEL: discord.TextChannel = None
STARTUP_ERRORS = []
BOT: commands.AutoShardedBot = None
LOG_PUMP = None
LOG_ERRORS = 0

log_type = namedtuple("Log_type", "category emoji")
LOG_TYPES = {
    "raid_new": log_type('RAID_LOGS', 'BAD_USER'),
    "raid_terminated": log_type("RAID_LOGS", 'INNOCENT'),
    'censored_message': log_type('CENSORED_MESSAGES', 'WARNING'),
    'censor_message_failed': log_type('CENSORED_MESSAGES', 'WARNING'),
    'censored_invite': log_type('CENSORED_MESSAGES', 'WARNING'),
    'invite_censor_fail': log_type('CENSORED_MESSAGES', 'WARNING'),
    'invite_censor_forbidden': log_type('CENSORED_MESSAGES', 'WARNING'),
    'automod_ban_failed': log_type('MOD_ACTIONS', 'WARNING'),
    'warning_added_modlog': log_type('MOD_ACTIONS', 'WARNING'),
    'warning_could_not_dm': log_type('MOD_ACTIONS', 'WARNING'),
    'inf_delete_log': log_type('MOD_ACTIONS', 'DELETE'),
    'ban_log': log_type('MOD_ACTIONS', 'BAN'),
    'kick_log': log_type('MOD_ACTIONS', 'BOOT'),
    'mute_role_already_removed': log_type('MOD_ACTIONS', 'WARNING'),
    'unmute_missing_perms': log_type('MOD_ACTIONS', 'WARNING'),
    'unmute_unknown_error': log_type('MOD_ACTIONS', 'WARNING'),
    'unmuted': log_type('MOD_ACTIONS', 'INNOCENT'),
    'tempban_expired_missing_perms': log_type('MOD_ACTIONS', 'WARNING'),
    'tempban_already_lifted': log_type('MOD_ACTIONS', 'WARNING'),
    'tempban_lifted': log_type('MOD_ACTIONS', 'INNOCENT'),
    'softban_log': log_type('MOD_ACTIONS', 'BAN'),
    'forceban_log': log_type('MOD_ACTIONS', 'BAN'),
    'mute_log': log_type('MOD_ACTIONS', 'MUTE'),
    'mute_duration_extended_log': log_type('MOD_ACTIONS', 'MUTE'),
    'mute_duration_added_log': log_type('MOD_ACTIONS', 'MUTE'),
    'mute_duration_overwritten_log': log_type('MOD_ACTIONS', 'MUTE'),
    'mute_reapply_log': log_type('MOD_ACTIONS', 'BAD_USER'),
    'mute_reapply_failed_log': log_type('MOD_ACTIONS', 'WARNING'),
    'tempban_log': log_type('MOD_ACTIONS', 'BAN'),
    'unban_log': log_type('MOD_ACTIONS', 'INNOCENT'),
    'unmute_modlog': log_type('MOD_ACTIONS', 'INNOCENT'),
    'channel_update_simple': log_type('CHANNEL_CHANGES', 'ALTER'),
    'channel_update_simple_by': log_type('CHANNEL_CHANGES', 'ALTER'),
    'role_update_simple': log_type('ROLE_CHANGES', 'ALTER'),
    'role_update_simple_by': log_type('ROLE_CHANGES', 'ALTER'),
    'command_used': log_type('ROLE_CHANGES', 'WRENCH'),
    'channel_created_by': log_type('ROLE_CHANGES', 'CREATE'),
    'channel_created': log_type('ROLE_CHANGES', 'CREATE'),
    'channel_deleted_by': log_type('channel_deleted_by', 'DELETE'),
    'channel_deleted': log_type('channel_deleted_by', 'DELETE'),
    'permission_override_update': log_type('CHANNEL_CHANGES', 'ALTER'),
    'permission_override_update_by': log_type('CHANNEL_CHANGES', 'ALTER'),
    'permission_override_update_role': log_type('CHANNEL_CHANGES', 'ALTER'),
    'permission_override_update_role_by': log_type('CHANNEL_CHANGES', 'ALTER'),
    'permission_override_removed': log_type('CHANNEL_CHANGES', 'ALTER'),
    'permission_override_removed_by': log_type('CHANNEL_CHANGES', 'ALTER'),
    'permission_override_removed_role': log_type('CHANNEL_CHANGES', 'ALTER'),
    'permission_override_removed_role_by': log_type('CHANNEL_CHANGES', 'ALTER'),
    'permission_override_added': log_type('CHANNEL_CHANGES', 'ALTER'),
    'permission_override_added_by': log_type('CHANNEL_CHANGES', 'ALTER'),
    'permission_override_added_role': log_type('CHANNEL_CHANGES', 'ALTER'),
    'permission_override_added_role_by': log_type('CHANNEL_CHANGES', 'ALTER'),
    'role_created_by': log_type('ROLE_CHANGES', 'CREATE'),
    'role_created': log_type('ROLE_CHANGES', 'CREATE'),
    'role_deleted': log_type('ROLE_CHANGES', 'DELETE'),
    'role_update_perm_added': log_type('ROLE_CHANGES', 'ALTER'),
    'role_update_perm_added_by': log_type('ROLE_CHANGES', 'DELETE'),
    'role_update_perm_revoked': log_type('ROLE_CHANGES', 'DELETE'),
    'role_update_perm_revoked_by': log_type('ROLE_CHANGES', 'DELETE'),
    'manual_ban_log': log_type('MOD_ACTIONS', 'BAN'),
    'join_logging': log_type('JOIN_LOGS', 'JOIN'),
    'leave_logging': log_type('JOIN_LOGS', 'LEAVE'),
    'manual_unban_log': log_type('MOD_ACTIONS', 'INNOCENT'),
    'own_nickname_changed': log_type('NAME_CHANGES', 'NICKTAG'),
    'unknown_nickname_changed': log_type('NAME_CHANGES', 'NICKTAG'),
    'mod_nickname_changed': log_type('NAME_CHANGES', 'NICKTAG'),
    'unknown_nickname_added': log_type('NAME_CHANGES', 'NICKTAG'),
    'own_nickname_added': log_type('NAME_CHANGES', 'NICKTAG'),
    'mod_nickname_added': log_type('NAME_CHANGES', 'NICKTAG'),
    'own_nickname_removed': log_type('NAME_CHANGES', 'NICKTAG'),
    'mod_nickname_removed': log_type('NAME_CHANGES', 'NICKTAG'),
    'role_removed_by': log_type('ROLE_CHANGES', 'ROLE_REMOVE'),
    'role_added_by': log_type('ROLE_CHANGES', 'ROLE_ADD'),
    'role_removed': log_type('ROLE_CHANGES', 'ROLE_REMOVE'),
    'role_added': log_type('ROLE_CHANGES', 'ROLE_ADD'),
    'message_removed': log_type('EDIT_LOGS', 'TRASH'),
    'edit_logging': log_type('EDIT_LOGS', 'EDIT'),
    'username_changed': log_type('NAME_CHANGES', 'NAMETAG'),
    'voice_change_deaf_true': log_type('VOICE_CHANGES_DETAILED', 'VOICE'),
    'voice_change_deaf_false': log_type('VOICE_CHANGES_DETAILED', 'VOICE'),
    'voice_change_mute_true': log_type('VOICE_CHANGES_DETAILED', 'VOICE'),
    'voice_change_mute_false': log_type('VOICE_CHANGES_DETAILED', 'VOICE'),
    'voice_change_self_mute_true': log_type('VOICE_CHANGES_DETAILED', 'VOICE'),
    'voice_change_self_mute_false': log_type('VOICE_CHANGES_DETAILED', 'VOICE'),
    'voice_change_self_deaf_true': log_type('VOICE_CHANGES_DETAILED', 'VOICE'),
    'voice_change_self_deaf_false': log_type('VOICE_CHANGES_DETAILED', 'VOICE'),
    'voice_change_afk_true': log_type('VOICE_CHANGES_DETAILED', 'VOICE'),
    'voice_change_afk_false': log_type('VOICE_CHANGES_DETAILED', 'VOICE'),
    'connected_to_voice': log_type('VOICE_CHANGES', 'VOICE'),
    'disconnected_voice': log_type('VOICE_CHANGES', 'VOICE'),
    'moved_voice': log_type('VOICE_CHANGES', 'VOICE'),
    'purged_log': log_type('EDIT_LOGS', 'DELETE'),
    'raid_mute_failed_no_role': log_type('RAID_LOGS', 'BAD_USER'),
    'raid_message_failed': log_type('RAID_LOGS', 'BAD_USER'),
    'raid_notification_failed': log_type('RAID_LOGS', 'BAD_USER'),
    'raid_notification_forbidden': log_type('RAID_LOGS', 'BAD_USER'),
    'raid_shield_triggered': log_type('RAID_LOGS', 'BAD_USER'),
    'raid_shield_terminated': log_type('RAID_LOGS', 'INNOCENT'),
    'raid_notification_forbidden': log_type('RAID_LOGS', 'BAD_USER'),



}

def before_send(event, hint):
    if event['level'] == "error" and 'logger' in event.keys() and event['logger'] == 'gearbot':
        return None  # we send errors manually, in a much cleaner way
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        for t in [ConnectionClosed, ClientOSError, ServerDisconnectedError]:
            if isinstance(exc_value, t):
                return
            event['fingerprint'] = ['database-unavailable']
    return event


def init_logger():
    # track commits to make sentry versions
    dsn = Configuration.get_master_var('SENTRY_DSN', '')
    if dsn != '':
        sentry_sdk.init(dsn, before_send=before_send)

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

    # handler = TimedRotatingFileHandler(filename='logs/discord.log', encoding='utf-8', when="h", interval=1, backupCount=24)

    # DISCORD_LOGGER.addHandler(handler)


async def initialize(bot: commands.Bot, channelID):
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
    global BOT_LOG_CHANNEL, STARTUP_ERRORS
    if BOT_LOG_CHANNEL is not None:
        return await BOT_LOG_CHANNEL.send(content=message, embed=embed)
    else:
        STARTUP_ERRORS.append(bot_log(message, embed))


def log_raw(guild_id, location, message=None, embed=None, file=None):
    channels = Configuration.get_var(guild_id, "LOG_CHANNELS")
    for cid, info in channels.items():
        if location in info:
            LOG_PUMP.receive(cid, (message, embed, file))


def log_to(guild_id, key, embed=None, file=None, can_stamp=True, tag_on=None, **kwargs):
    info = LOG_TYPES[key]
    remaining = None
    if key is None and embed is None and file is None:
        raise ValueError("What the heck is trying to log nothing?")
    stamp = f"[``{datetime.strftime(datetime.now().astimezone(pytz.timezone(Configuration.get_var(guild_id, 'TIMEZONE'))), '%H:%M:%S')}``] " if can_stamp and Configuration.get_var(guild_id, "TIMESTAMPS") else ""
    m = MessageUtils.assemble(guild_id, info.emoji, key, **kwargs).replace('@', '@\u200b')
    message = f"{stamp}{Utils.trim_message(m, 1985)}"
    if tag_on is not None:
        tag_on = tag_on.replace('@', '@\u200b')
        if message is None:
            message = tag_on.replace('@', '@\u200b')
        else:
            if len(message) + len(tag_on) <= 1999:
                message = f"{message} {tag_on}"
            else:
                remaining = tag_on
    if message is not None:
        message = Utils.trim_message(message, 1999)
    channels = Configuration.get_var(guild_id, "LOG_CHANNELS")

    for cid, logging_keys in channels.items():
        if info.category in logging_keys:
            if remaining is None:
                LOG_PUMP.receive(cid, (message, embed, file))
            else:
                LOG_PUMP.receive(cid, (message, None, None))
                LOG_PUMP.receive(cid, (tag_on, embed, file))


async def message_owner(bot, message):
    if bot.owner_id is None:
        app = await bot.application_info()
        bot.owner_id = app.owner.id
    owner = bot.get_user(bot.owner_id)
    await owner.send(message)


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
                empty = []
                senders = []
                embed = file = None
                for cid, todo in self.todo.items():
                    channel = BOT.get_channel(int(cid))
                    if channel is not None and len(todo) > 0:
                        permissions = channel.permissions_for(channel.guild.me)
                        to_send = ""
                        while len(todo) > 0:
                            message, embed, file = todo[0]
                            if message is None or message.strip() == "":
                                message = ""
                            if (not permissions.send_messages) or (
                                    embed is not None and not permissions.embed_links) or (
                                    file is not None and not permissions.attach_files):
                                todo.pop(0)
                                continue
                            elif len(to_send) + len(message) <= 1999:
                                to_send += f"{message}\n"
                                todo.pop(0)
                            else:
                                break
                            if embed is not None or file is not None:
                                break
                        try:
                            senders.append(channel.send(to_send if to_send != "" else None, embed=embed, file=file))
                        except Exception as e:
                            await TheRealGearBot.handle_exception("LOG PUMP", BOT, e,
                                                                  cid=cid, todo=todo, to_send=to_send,
                                                                  LOG_CACHE=self.todo, embed=embed,
                                                                  file=file, empty=empty)
                    else:
                        empty.append(cid)
                for e in empty:
                    del self.todo[e]
                for s in senders:
                    try:
                        await s
                    except discord.Forbidden:
                        pass
                    except Exception as e:
                        await log_error()
                        await TheRealGearBot.handle_exception("LOG PUMP", BOT, e,
                                                              cid=cid, todo=todo, to_send=to_send,
                                                              LOG_CACHE=self.todo, embed=embed, file=file,
                                                              empty=empty)
                await asyncio.sleep(0.1)
            except CancelledError:
                return  # we're shutting down
            except Exception as e:
                await log_error()
                await TheRealGearBot.handle_exception("LOG PUMP", BOT, e,
                                                      cid=cid, todo=todo, to_send=to_send,
                                                      LOG_CACHE=self.todo, embed=embed, file=file,
                                                      empty=empty)
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
