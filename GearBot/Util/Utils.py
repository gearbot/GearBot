import asyncio
import json
import os
import subprocess
import time
from collections import namedtuple, OrderedDict
from datetime import datetime
from subprocess import Popen

import discord
from discord import NotFound

from Util import GearbotLogging, Translator, Emoji
from Util.Matchers import ROLE_ID_MATCHER, CHANNEL_ID_MATCHER, ID_MATCHER, EMOJI_MATCHER, URL_MATCHER

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


async def cleanExit(bot, trigger):
    await GearbotLogging.bot_log(f"Shutdown triggered by {trigger}.")
    await bot.logout()
    await bot.close()
    bot.aiosession.close()


def trim_message(message, limit):
    if len(message) < limit - 3:
        return message
    return f"{message[:limit-3]}..."




async def clean(text, guild:discord.Guild=None, markdown=True, links=True, emoji=True):
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

        # re-assemble emoji so such a way that they don't turn into twermoji

    if markdown:
        text = escape_markdown(text)
    else:
        text = text.replace("@", "@\u200b").replace("**", "*​*").replace("``", "`​`")

    if emoji:
        for e in set(EMOJI_MATCHER.findall(text)):
            a, b, c = zip(e)
            text = text.replace(f"<{a[0]}:{b[0]}:{c[0]}>", f"<{a[0]}\\:{b[0]}\\:{c[0]}>")

    if links:
        #find urls last so the < escaping doesn't break it
        for url in set(URL_MATCHER.findall(text)):
            text = text.replace(url, f"<{url}>")

    return text

def escape_markdown(text):
    text = str(text)
    for c in ["\\", "`", "*", "_", "~", "|", "{"]:
        text = text.replace(c, f"\\{c}")
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
        return f"{user.name}#{user.discriminator}"


async def get_user(uid, fetch=True):
    UserClass = namedtuple("UserClass", "name id discriminator bot avatar_url created_at is_avatar_animated mention")
    user = BOT.get_user(uid)
    if user is None:
        if uid in known_invalid_users:
            return None

        if BOT.redis_pool is not None:
            userCacheInfo = await BOT.redis_pool.hgetall(uid)

            if len(userCacheInfo) == 8: # It existed in the Redis cache, check length cause sometimes somehow things are missing, somehow
                userFormed = UserClass(
                    userCacheInfo["name"],
                    userCacheInfo["id"],
                    userCacheInfo["discriminator"],
                    userCacheInfo["bot"] == "1",
                    userCacheInfo["avatar_url"],
                    datetime.fromtimestamp(float(userCacheInfo["created_at"])),
                    bool(userCacheInfo["is_avatar_animated"]) == "1",
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
                        bot = int(user.bot),
                        avatar_url = user.avatar_url,
                        created_at = user.created_at.timestamp(),
                        is_avatar_animated = int(user.is_avatar_animated()),
                        mention = user.mention
                    )

                    pipeline.expire(uid, 3000) # 5 minute cache life
                    
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
    if user is None:
        return "UNKNOWN USER"
    return f"{escape_markdown(user.name)}#{user.discriminator}"

def username_from_user(user):
    if user is None:
        return "UNKNOWN USER"
    return user.name

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


def server_info(guild, request_guild=None):
    guild_features = ", ".join(guild.features)
    if guild_features == "":
        guild_features = None
    guild_made = guild.created_at.strftime("%d-%m-%Y")
    embed = discord.Embed(color=guild.roles[-1].color, timestamp=datetime.fromtimestamp(time.time()))
    embed.set_thumbnail(url=guild.icon_url)
    embed.add_field(name=Translator.translate('server_name', request_guild), value=guild.name, inline=True)
    embed.add_field(name=Translator.translate('id', request_guild), value=guild.id, inline=True)
    embed.add_field(name=Translator.translate('owner', request_guild), value=guild.owner, inline=True)
    embed.add_field(name=Translator.translate('members', request_guild), value=guild.member_count, inline=True)
    embed.add_field(name=Translator.translate('text_channels', request_guild), value=str(len(guild.text_channels)),
                    inline=True)
    embed.add_field(name=Translator.translate('voice_channels', request_guild), value=str(len(guild.voice_channels)),
                    inline=True)
    embed.add_field(name=Translator.translate('total_channel', request_guild),
                    value=str(len(guild.text_channels) + len(guild.voice_channels)),
                    inline=True)
    embed.add_field(name=Translator.translate('created_at', request_guild),
                    value=f"{guild_made} ({(datetime.fromtimestamp(time.time()) - guild.created_at).days} days ago)",
                    inline=True)
    embed.add_field(name=Translator.translate('vip_features', request_guild), value=guild_features, inline=True)
    if guild.icon_url != "":
        embed.add_field(name=Translator.translate('server_icon', request_guild),
                        value=f"[{Translator.translate('server_icon', request_guild)}]({guild.icon_url})", inline=True)
    roles = ", ".join(role.name for role in guild.roles)
    embed.add_field(name=Translator.translate('all_roles', request_guild),
                    value=roles if len(roles) < 1024 else f"{len(guild.roles)} roles", inline=True)
    if guild.emojis:
        emoji = "".join(str(e) for e in guild.emojis)
        embed.add_field(name=Translator.translate('emoji', request_guild),
                        value=emoji if len(emoji) < 1024 else f"{len(guild.emojis)} emoji")
    statuses = dict(online=0, idle=0, dnd=0, offline=0)
    for m in guild.members:
        statuses[str(m.status)] += 1
    embed.add_field(name=Translator.translate('member_statuses', request_guild), value="\n".join(f"{Emoji.get_chat_emoji(status.upper())} {Translator.translate(status, request_guild)}: {count}" for status, count in statuses.items()))
    if guild.splash_url != "":
        embed.set_image(url=guild.splash_url)
    return embed


def time_difference(begin, end, location):
    diff = begin - end
    minutes, seconds = divmod(diff.days * 86400 + diff.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return (Translator.translate('days', location, days=diff.days)) if diff.days > 0 else Translator.translate('hours',
                                                                                                               location,
                                                                                                               hours=hours,
                                                                                                               minutes=minutes)

def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i+n]