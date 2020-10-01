import io
import logging
import os
import sys
import traceback
from collections import namedtuple
from concurrent.futures import CancelledError
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from queue import Queue

import discord
import pytz
import sentry_sdk
from aiohttp import ClientOSError, ServerDisconnectedError
from discord import ConnectionClosed, AllowedMentions
from discord.ext import commands

from Bot import TheRealGearBot
from Util import Configuration, Utils, MessageUtils

LOGGER = logging.getLogger('gearbot')
DISCORD_LOGGER = logging.getLogger('discord')

BOT_LOG_CHANNEL: discord.TextChannel = None
STARTUP_ERRORS = []
BOT: commands.AutoShardedBot = None
LOG_ERRORS = 0

log_type = namedtuple("Log_type", "config_key category emoji")
todo = namedtuple("TODO", "message embed file")

LOGGING_INFO = {
    "CENSORED_MESSAGES": {
        "censor_fail": {
            "censored_message_failed": "WARNING",
            "censored_message_failed_word": "WARNING",
            "invite_censor_fail": "WARNING",
            "invite_censor_forbidden": "WARNING",
            "censored_message_failed_content": "WARNING"
        },
        "censored": {
            "censored_invite": "WARNING",
            "censored_message": "WARNING",
            "censored_message_word": "WARNING",
            "censored_message_domain_blocked": "WARNING",
            "censored_message_content": "WARNING",
            "censored_message_emoji_only": "WARNING"
        }
    },
    "CHANNEL_CHANGES": {
        "channel_log": {
            "channel_created": "CREATE",
            "channel_created_by": "CREATE",
            "channel_deleted": "DELETE",
            "channel_deleted_by": "DELETE"
        },
        "perm_overrides": {
            "permission_override_added": "ALTER",
            "permission_override_added_by": "ALTER",
            "permission_override_added_role": "ALTER",
            "permission_override_added_role_by": "ALTER",
            "permission_override_removed": "ALTER",
            "permission_override_removed_by": "ALTER",
            "permission_override_removed_role": "ALTER",
            "permission_override_removed_role_by": "ALTER",
            "permission_override_update": "ALTER",
            "permission_override_update_by": "ALTER",
            "permission_override_update_role": "ALTER",
            "permission_override_update_role_by": "ALTER"
        },
        "simple_change": {
            "channel_update_simple": "ALTER",
            "channel_update_simple_by": "ALTER"
        },
        "slowmode_log": "ALTER"
    },
    "CONFIG_CHANGES": {
        "config_change": "WRENCH",
        "config_dash_security_change": "WRENCH",
        "mute_role_changes": {
            "config_mute_cleanup_complete": "WRENCH",
            "config_mute_cleanup_failed": "WRENCH",
            "config_mute_cleanup_triggered": "WRENCH",
            "config_mute_role_changed": "WRENCH",
            "config_mute_role_disabled": "WRENCH",
            "config_mute_role_set": "WRENCH",
            "config_mute_setup_complete": "WRENCH",
            "config_mute_setup_failed": "WRENCH",
            "config_mute_setup_triggered": "WRENCH"
        },
        "perm_role_changes": {
            "config_change_role_added": "WRENCH",
            "config_change_role_removed": "WRENCH"
        },
        "logging_change": {
            "logging_channel_removed": "WRENCH",
            "logging_channel_removed_with_disabled": "WRENCH",
            "logging_channel_added": "WRENCH",
            "logging_channel_added_with_disabled": "WRENCH",
            "logging_category_added": "WRENCH",
            "logging_category_removed": "WRENCH",
            "logging_key_disabled": "WRENCH",
            "logging_key_enabled": "WRENCH"
        }
    },
    "FUTURE_LOGS": {},
    "MESSAGE_LOGS": {
        "edit_logging": "EDIT",
        "message_removed": "TRASH",
        "pins": {
            "message_pinned": "PIN",
            "message_pinned_by": "PIN",
            "message_unpinned": "PIN"
        },
        "purged_log": "DELETE"
    },
    "MISC": {
        "command_used": "WRENCH"
    },
    "MOD_ACTIONS": {
        "ban": {
            "ban_log": "BAN",
            "manual_ban_log": "BAN",
            "ban_could_not_dm": "WARNING" 
        },
        "errors": {
            "mute_reapply_failed_log": "WARNING",
            "mute_role_already_removed": "WARNING",
            "tempban_already_lifted": "WARNING",
            "tempban_expired_missing_perms": "WARNING",
            "unmute_missing_perms": "WARNING",
            "unmute_unknown_error": "WARNING"
        },
        "forceban_log": "BAN",
        "inf_delete_log": "DELETE",
        "kick_log": {
            "kick_log": "BOOT",
            "kick_could_not_dm": "WARNING" 
        },
        "mute_log": {
            "mute_duration_added_log": "MUTE",
            "mute_duration_extended_log": "MUTE",
            "mute_duration_overwritten_log": "MUTE",
            "mute_log": "MUTE",
            "mute_could_not_dm": "WARNING" 
        },
        "mute_reapply_log": "BAD_USER",
        "softban_log": "BAN",
        "tempban_lifted": "INNOCENT",
        "tempban_log": "BAN",
        "tempban_could_not_dm": "WARNING",
        "unban": {
            "manual_unban_log": "INNOCENT",
            "unban_log": "INNOCENT"
        },
        "unmute_modlog": "INNOCENT",
        "unmuted": {
            "unmuted": "INNOCENT",
            "unmute_could_not_dm": "WARNING"
        },
        "verification_log": "WRENCH",
        "warning": {
            "warning_added_modlog": "WARNING",
            "warning_could_not_dm": "WARNING"
        },
        "inf_update_log": "WARNING"
    },
    "NAME_CHANGES": {
        "nickname": {
            "mod_nickname_added": "NICKTAG",
            "mod_nickname_changed": "NICKTAG",
            "mod_nickname_removed": "NICKTAG",
            "own_nickname_added": "NICKTAG",
            "own_nickname_changed": "NICKTAG",
            "own_nickname_removed": "NICKTAG",
            "unknown_nickname_added": "NICKTAG",
            "unknown_nickname_changed": "NICKTAG",
            "unknown_nickname_removed": "NICKTAG"
        },
        "username_changed": "NAMETAG"
    },
    "RAID_LOGS": {
        "failures": {
            "raid_ban_forbidden": "WARNING",
            "raid_ban_unknown_error": "WARNING",
            "raid_kick_forbidden": "WARNING",
            "raid_kick_unknown_error": "WARNING",
            "raid_message_failed": "BAD_USER",
            "raid_message_failed_channel": "WARNING",
            "raid_message_failed_channel_unknown_error": "WARNING",
            "raid_message_failed_missing_channel": "WARNING",
            "raid_message_user_forbidden": "WARNING",
            "raid_message_user_not_found": "WARNING",
            "raid_mute_failed_no_role": "BAD_USER",
            "raid_mute_forbidden": "WARNING",
            "raid_mute_unknown_error": "WARNING",
            "raid_notification_failed": "BAD_USER",
            "raid_notification_forbidden": "BAD_USER",
            "shield_time_limit_reached": "WARNING"
        },
        "state_changes": {
            "raid_new": "BAD_USER",
            "raid_shield_terminated": "INNOCENT",
            "raid_shield_triggered": "BAD_USER",
            "raid_terminated": "INNOCENT"
        }
    },
    "ROLE_CHANGES": {
        "perm_update": {
            "role_update_perm_added": "ALTER",
            "role_update_perm_added_by": "ALTER",
            "role_update_perm_revoked": "DELETE",
            "role_update_perm_revoked_by": "DELETE"
        },
        "role_log": {
            "role_added": "ROLE_ADD",
            "role_added_by": "ROLE_ADD",
            "role_created": "CREATE",
            "role_created_by": "CREATE",
            "role_deleted": "DELETE",
            "role_deleted_by": "DELETE",
            "role_removed": "ROLE_REMOVE",
            "role_removed_by": "ROLE_REMOVE"
        },
        "simple_change": {
            "role_update_simple": "ALTER",
            "role_update_simple_by": "ALTER"
        }
    },
    "SPAM_VIOLATION": {
        "spam_violate": "BAD_USER"
    },
    "TRAVEL_LOGS": {
        "join_logging": {
            "join_logging": "JOIN",
            "join_logging_new": "JOIN"
        },
        "leave_logging": "LEAVE"
    },
    "VOICE_CHANGES": {
        "connected_to_voice": "VOICE",
        "disconnected_voice": "VOICE",
        "moved_voice": "VOICE"
    },
    "VOICE_CHANGES_DETAILED": {
        "voice_change_afk_false": "VOICE",
        "voice_change_afk_true": "VOICE",
        "voice_change_deaf_false": "VOICE",
        "voice_change_deaf_true": "VOICE",
        "voice_change_mute_false": "VOICE",
        "voice_change_mute_true": "VOICE",
        "voice_change_self_deaf_false": "VOICE",
        "voice_change_self_deaf_true": "VOICE",
        "voice_change_self_mute_false": "VOICE",
        "voice_change_self_mute_true": "VOICE"
    }
}

LOG_TYPES = dict()

LOG_QUEUE = dict()


def before_send(event, hint):
    if event['level'] == "error" and 'logger' in event.keys() and event['logger'] == 'gearbot':
        return None  # we send errors manually, in a much cleaner way
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        for t in [ConnectionClosed, ClientOSError, ServerDisconnectedError]:
            if isinstance(exc_value, t):
                return
    return event


def init_logger(cluster):
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
    handler = TimedRotatingFileHandler(filename=f'logs/gearbot_cluster_{cluster}.log', encoding='utf-8', when="midnight", backupCount=30)
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    DISCORD_LOGGER.addHandler(handler)
    LOGGER.addHandler(handler)

    # handler = TimedRotatingFileHandler(filename='logs/discord.log', encoding='utf-8', when="h", interval=1, backupCount=24)

    # DISCORD_LOGGER.addHandler(handler)


async def initialize(bot: commands.Bot, channelID):
    global BOT_LOG_CHANNEL, BOT, STARTUP_ERRORS
    BOT = bot
    BOT_LOG_CHANNEL = await bot.fetch_channel(int(channelID))
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

    for cat, info in LOGGING_INFO.items():
        for k, v in info.items():
            if isinstance(v, dict):
                for inner, emoji in v.items():
                    LOG_TYPES[inner] = log_type(k, cat, emoji)
            else:
                LOG_TYPES[k] = log_type(k, cat, v)


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


def log_raw(guild_id, key, message=None, embed=None, file=None):
    # logging category, emoji and
    info = LOG_TYPES[key]

    # determine where it should be logged so we don't need to bother assembling everything when it's just gona be voided anyways
    targets = []
    channels = Configuration.get_var(guild_id, "LOG_CHANNELS")
    for cid, settings in channels.items():
        if info.category in settings["CATEGORIES"] and info.config_key not in settings["DISABLED_KEYS"]:
            targets.append(cid)

    # no targets? no logging
    if len(targets) is 0:
        return
    log_to(guild_id, targets, Utils.trim_message(message, 2000) if message is not None else None, embed, file, None)


def log_key(guild_id, key, embed=None, file=None, can_stamp=True, tag_on=None, **kwargs):
    # logging category, emoji and
    info = LOG_TYPES[key]

    # determine where it should be logged so we don't need to bother assembling everything when it's just gona be voided anyways
    targets = []
    channels = Configuration.get_var(guild_id, "LOG_CHANNELS")
    for cid, settings in channels.items():
        if info.category in settings["CATEGORIES"] and info.config_key not in settings["DISABLED_KEYS"]:
            targets.append(cid)

    # no targets? don't bother with assembly
    if len(targets) is 0:
        return

    message = MessageUtils.assemble(guild_id, info.emoji, key, **kwargs).replace('@', '@\u200b')

    if can_stamp and Configuration.get_var(guild_id, 'GENERAL', "TIMESTAMPS"):
        s = datetime.strftime(
            datetime.now().astimezone(pytz.timezone(Configuration.get_var(guild_id, 'GENERAL', 'TIMEZONE'))),
            '%H:%M:%S')
        stamp = f"[``{s}``] "
        message = Utils.trim_message(f'{stamp} {message}', 2000)

    if tag_on is not None:
        tag_on = tag_on.replace('@', '@\u200b')

    if tag_on is not None and len(message) + len(tag_on) <= 1998:
        message = f"{message} {tag_on}"
        tag_on = None

    message = Utils.trim_message(message, 2000)
    # queuing up
    log_to(guild_id, targets, message, embed, file, tag_on)


def log_to(guild_id, targets, message, embed, file, tag_on=None):
    for target in targets:
        # make sure we have a queue and a running task
        if target not in LOG_QUEUE:
            LOG_QUEUE[target] = Queue()
            BOT.loop.create_task(log_task(guild_id, target))

        # duplicate the file bytes so it doesn't freak out when we try to send it twice
        f = None
        if file is not None:
            buffer = file[0]
            name = file[1]
            buffer.seek(0)
            b2 = io.BytesIO()
            for line in buffer.readlines():
                b2.write(line)
            b2.seek(0)
            f = discord.File(b2, name)

        # actually adding to the queue
        if tag_on is None:
            LOG_QUEUE[target].put(todo(message, embed, f))
        else:
            LOG_QUEUE[target].put(todo(message, None, None))
            LOG_QUEUE[target].put(todo(tag_on, embed, f))


async def log_task(guild_id, target):
    to_send = ""
    todo = None
    # keep pumping until we run out of messages
    while not LOG_QUEUE[target].empty():
        try:
            channel = BOT.get_channel(int(target))
            # channel no longer exists, abort and re-validate config to remove the invalid entry
            if channel is None:
                del LOG_QUEUE[target]
                Configuration.validate_config(guild_id)
                return
            # pull message from queue
            todo = LOG_QUEUE[target].get(block=False)
            if (len(to_send) + len(todo.message) if todo.message is not None else 0) < 2000:
                to_send = f'{to_send}\n{todo.message if todo.message is not None else ""}'
            else:
                # too large, send it out
                await channel.send(to_send, allowed_mentions=AllowedMentions(everyone=False, users=False, roles=False))
                to_send = todo.message
            if todo.embed is not None or todo.file is not None or LOG_QUEUE[target].empty():
                await channel.send(to_send, embed=todo.embed, file=todo.file, allowed_mentions=AllowedMentions(everyone=False, users=False, roles=False))
                to_send = ""
        except discord.Forbidden:
            # someone screwed up their permissions, not my problem, will show an error in the dashboard
            del LOG_QUEUE[target]
            return
        except CancelledError:
            return  # bot is terminating
        except Exception as e:
            del LOG_QUEUE[target]
            await TheRealGearBot.handle_exception("LOG PUMP", BOT, e,
                                                  cid=target, todo=todo, to_send=to_send)
            return
    del LOG_QUEUE[target]


async def message_owner(bot, message):
    if bot.owner_id is None:
        app = await bot.application_info()
        bot.owner_id = app.owner.id
    owner = bot.get_user(bot.owner_id)
    await owner.send(message)
