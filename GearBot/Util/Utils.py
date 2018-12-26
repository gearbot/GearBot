import asyncio
import datetime
import json
import os
import re
import subprocess
import time
from subprocess import Popen
from collections import namedtuple, OrderedDict
from datetime import datetime

import discord
from discord import NotFound

from Util import GearbotLogging, Translator

BOT = None


def initialize(actual_bot):
    global BOT
    BOT = actual_bot


def fetch_from_disk(filename, alternative=None):
    try:
        with open(f"{filename}.json") as file:
            return json.load(file)
    except FileNotFoundError:
        if alternative is not None:
            fetch_from_disk(alternative)
        return dict()

def saveToDisk(filename, dict):
    with open(f"{filename}.json", "w") as file:
        json.dump(dict, file, indent=4, skipkeys=True, sort_keys=True)

def convertToSeconds(value: int, type: str):
    type = type.lower()
    if len(type) > 1 and type[-1:] == 's': # plural -> singular
        type = type[:-1]
    if type == 'w' or type == 'week':
        value = value * 7
        type = 'd'
    if type == 'd' or type == 'day':
        value = value * 24
        type = 'h'
    if type == 'h' or type == 'hour':
        value = value * 60
        type = 'm'
    if type == 'm' or type == 'minute':
        value = value * 60
        type = 's'
    if type != 's' and type != 'second':
        return None
    else:
        return value

async def cleanExit(bot, trigger):
    await GearbotLogging.bot_log(f"Shutdown triggered by {trigger}.")
    await bot.logout()
    await bot.close()
    bot.aiosession.close()


def trim_message(message, limit):
    if len(message) < limit - 3:
        return message
    return f"{message[:limit-3]}..."


ID_MATCHER = re.compile("<@!?([0-9]+)>")
ROLE_ID_MATCHER = re.compile("<@&([0-9]+)>")
CHANNEL_ID_MATCHER = re.compile("<#([0-9]+)>")
URL_MATCHER = re.compile(r'((?:https?://)[a-z0-9]+(?:[-.][a-z0-9]+)*\.[a-z]{2,5}(?::[0-9]{1,5})?(?:/[^ \n]*)?)', re.IGNORECASE)

async def clean(text, guild:discord.Guild=None, markdown=True, links=True):
    text = str(text)
    if guild is not None:
        # resolve user mentions
        for uid in set(ID_MATCHER.findall(text)):
            name = "@" + await username(int(uid), False, False)
            text = text.replace(f"<@{uid}>", name)
            text = text.replace(f"<@!{uid}>", name)

        # resolve role mentions
        for uid in set(ROLE_ID_MATCHER.findall(text)):
            role = discord.utils.get(guild.roles, id=int(uid))
            if role is None:
                name = "@UNKNOWN ROLE"
            else:
                name = "@" + role.name
            text = text.replace(f"<@&{uid}>", name)

        # resolve channel names
        for uid in set(CHANNEL_ID_MATCHER.findall(text)):
            channel = guild.get_channel(uid)
            if channel is None:
                name = "#UNKNOWN CHANNEL"
            else:
                name = "#" + channel.name
            text = text.replace(f"<@#{uid}>", name)

    if markdown:
        text = escape_markdown(text)
    else:
        text = text.replace("@", "@\u200b").replace("**", "*​*").replace("``", "`​`")

    if links:
        #find urls last so the < escaping doesn't break it
        for url in URL_MATCHER.findall(text):
            text = text.replace(url, f"<{url}>")


    return text

def escape_markdown(text):
    text = str(text)
    for c in ("\\", "`", "*", "_", "~", "<"):
        text = text.replace(c, f"\{c}\u200b")
    return text.replace("@", "@\u200b")

def clean_name(text):
    if text is None:
        return None
    return str(text).replace("@","@\u200b").replace("**", "*\u200b*").replace("``", "`\u200b`")


known_invalid_users = []
user_cache = OrderedDict()


async def username(uid, fetch=True, clean=True):
    user = await get_user(uid, fetch)
    if user is None:
        return "UNKNOWN USER"
    if clean:
        return clean_user(user)
    else:
        return str(user)


async def get_user(uid, fetch=True):
    UserClass = namedtuple("UserClass", "name id discriminator avatar bot avatar_url created_at is_avatar_animated mention")
    user = BOT.get_user(uid)
    if user is None:
        if uid in known_invalid_users:
            return None

        if BOT.redis_pool != None:
            userCacheInfo = await BOT.redis_pool.hgetall(uid)

            if userCacheInfo != {}: # It existed in the Redis cache
                userFormed = UserClass(
                    userCacheInfo["name"],
                    userCacheInfo["id"],
                    userCacheInfo["discriminator"],
                    userCacheInfo["avatar"],
                    bool(userCacheInfo["bot"]),
                    userCacheInfo["avatar_url"],
                    datetime.fromtimestamp(float(userCacheInfo["created_at"])),
                    bool(userCacheInfo["is_avatar_animated"]),
                    userCacheInfo["mention"]
                )

                return userFormed
            if fetch:
                try:
                    user = await BOT.get_user_info(uid)
                    pipeline = BOT.redis_pool.pipeline()

                    pipeline.hmset_dict(uid,
                        name = user.name,
                        id = user.id,
                        discriminator = user.discriminator,
                        avatar = user.avatar,
                        bot = str(user.bot),
                        avatar_url = user.avatar_url,
                        created_at = int(datetime.timestamp(user.created_at)),
                        is_avatar_animated = str(user.is_avatar_animated()),
                        mention = user.mention
                    )

                    pipeline.expire(uid, 300) # 5 minute cache life
                    
                    BOT.loop.create_task(pipeline.execute())

                except NotFound:
                    known_invalid_users.append(uid)
                    return None
        else: # No Redis, using the dict method instead
            if uid in user_cache:
                return user_cache[uid]
            if fetch:
                try:
                    user = await BOT.get_user_info(uid)
                    if len(user_cache) >= 10: # Limit the cache size to the most recent 10
                        user_cache.popitem()
                    user_cache[uid] = user
                except NotFound:
                    known_invalid_users.append(uid)
                    return None
    return user


def clean_user(user):
    return f"\u200b{escape_markdown(user.name)}\u200b#{user.discriminator}"

def pad(text, length, char=' '):
    return f"{text}{char * (length-len(text))}"

async def execute(command):
    p = Popen(command, cwd=os.getcwd(), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while p.poll() is None:
        await asyncio.sleep(1)
    out, error = p.communicate()
    return p.returncode, out, error

def find_key(data, wanted):
    for k, v in data.items():
        if v == wanted:
            return k


def server_info(guild):
    guild_features = ", ".join(guild.features)
    if guild_features == "":
        guild_features = None
    guild_made = guild.created_at.strftime("%d-%m-%Y")
    embed = discord.Embed(color=0x7289DA, timestamp=datetime.datetime.fromtimestamp(time.time()))
    embed.set_thumbnail(url=guild.icon_url)
    embed.add_field(name=Translator.translate('name', guild), value=guild.name, inline=True)
    embed.add_field(name=Translator.translate('id', guild), value=guild.id, inline=True)
    embed.add_field(name=Translator.translate('owner', guild), value=guild.owner, inline=True)
    embed.add_field(name=Translator.translate('members', guild), value=guild.member_count, inline=True)
    embed.add_field(name=Translator.translate('text_channels', guild), value=str(len(guild.text_channels)),
                    inline=True)
    embed.add_field(name=Translator.translate('voice_channels', guild), value=str(len(guild.voice_channels)),
                    inline=True)
    embed.add_field(name=Translator.translate('total_channel', guild),
                    value=str(len(guild.text_channels) + len(guild.voice_channels)),
                    inline=True)
    embed.add_field(name=Translator.translate('created_at', guild),
                    value=f"{guild_made} ({(datetime.datetime.fromtimestamp(time.time()) - guild.created_at).days} days ago)",
                    inline=True)
    embed.add_field(name=Translator.translate('vip_features', guild), value=guild_features, inline=True)
    if guild.icon_url != "":
        embed.add_field(name=Translator.translate('server_icon', guild),
                        value=f"[{Translator.translate('server_icon', guild)}]({guild.icon_url})", inline=True)
    roles = ", ".join(role.name for role in guild.roles)
    embed.add_field(name=Translator.translate('all_roles', guild),
                    value=roles if len(roles) < 1024 else f"{len(guild.roles)} roles", inline=True)
    if guild.emojis:
        emoji = "".join(str(e) for e in guild.emojis)
        embed.add_field(name=Translator.translate('emoji', guild),
                        value=emoji if len(emoji) < 1024 else f"{len(guild.emojis)} emoji")
    return embed


def time_difference(begin, end, location):
    diff = begin - end
    minutes, seconds = divmod(diff.days * 86400 + diff.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return (Translator.translate('days', location, days=diff.days)) if diff.days > 0 else Translator.translate('hours',
                                                                                                               location,
                                                                                                               hours=hours,
                                                                                                               minutes=minutes)
