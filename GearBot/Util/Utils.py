import asyncio
import datetime
import json
import os
import re
import subprocess
import time
from subprocess import Popen

import discord
from discord import NotFound

from Util import GearbotLogging, Translator

BOT = None
cache_task = None

class CacheCleaner:

    def __init__(self) :
        self.running = True

    async def run(self):
        while not BOT.is_closed() and self.running:
            known_invalid_users.clear()
            user_cache.clear()
            await asyncio.sleep(5 * 60)


def on_ready(actual_bot):
    global BOT, cache_task
    BOT = actual_bot
    cache_task = CacheCleaner()
    BOT.loop.create_task(cache_task.run())



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

async def clean(text, guild:discord.Guild=None):
    text = str(text)
    if guild is not None:
        # resolve user mentions
        for uid in set(ID_MATCHER.findall(text)):
            name = "@" + await username(int(uid), False)
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


    text = escape_markdown(text)

    #find urls last so the < escaping doesn't break it
    for url in URL_MATCHER.findall(text):
        text = text.replace(url, f"<{url}>")


    # make sure we don't have funny guys/roles named "everyone" messing it all up
    text = text.replace("@", "@\u200b")
    return text

def escape_markdown(text):
    for c in ("\\", "`", "*", "_", "~", "<"):
        text = text.replace(c, f"\{c}\u200b")
    return text

def clean_name(text):
    if text is None:
        return None
    return text.replace("@","@\u200b")


known_invalid_users = []
user_cache = {}


async def username(uid, fetch=True):
    user = await get_user(uid, fetch)
    if user is None:
        return "UNKNOWN USER"
    return clean_user(user)


async def get_user(uid, fetch=True):
    user = BOT.get_user(uid)
    if user is None:
        if uid in known_invalid_users:
            return None

        if uid in user_cache:
            return user_cache[uid]

        if fetch:
            try:
                user = await BOT.get_user_info(uid)
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
