import asyncio
import json
import os
import subprocess
from subprocess import Popen

from discord import NotFound
from discord.ext import commands
from discord.ext.commands import UserConverter, BadArgument

from Util import GearbotLogging

bot = None

def on_ready(actual_bot):
    global bot
    bot = actual_bot
    bot.loop.create_task(cache_nuke())

async def cache_nuke():
    while not bot.is_closed():
        known_invalid_users.clear()
        user_cache.clear()
        await asyncio.sleep(5*60)


def fetchFromDisk(filename):
    try:
        with open(f"{filename}.json") as file:
            return json.load(file)
    except FileNotFoundError:
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
        raise commands.BadArgument(f"Invalid duration: `{type}`\nValid identifiers: week(s), day(s), hour(s), minute(s), second(s)")
    else:
        return value

async def cleanExit(bot, trigger):
    await GearbotLogging.logToBotlog(f"Shutdown triggered by {trigger}.")
    await bot.logout()
    await bot.close()
    bot.aiosession.close()


def trim_message(message, limit):
    if len(message) < limit - 3:
        return message
    return f"{message[:limit-3]}..."


def clean(text):
    return text.replace("@","@\u200b").replace("`", "")

known_invalid_users = []
user_cache = {}

async def username(id):
    user = get_user(id)
    if user is None:
        return "UNKNOWN USER"
    return clean_user(user)

async def get_user(id):
    if id in known_invalid_users:
        return None
    if id in user_cache:
        return user_cache[id]
    user = bot.get_user(id)
    if user is None:
        try:
            user = await bot.get_user_info(id)
            user_cache[id] = user
        except NotFound:
            known_invalid_users.append(id)
            return None
    return user

def clean_user(user):
    return f"{user.name}#{user.discriminator}"

def pad(text, length, char=' '):
    return f"{text}{char * (length-len(text))}"

async def execute(command):
    p = Popen(command, cwd=os.getcwd(), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while p.poll() is None:
        await asyncio.sleep(1)
    out, error = p.communicate()
    return p.returncode, out, error

async def conver_to_id(ctx, user):
    duser = None
    try:
        duser = (await UserConverter().convert(ctx, user)).id
    except BadArgument as ex:
        try:
            duser = int(user)
        except ValueError:
            pass
    return duser