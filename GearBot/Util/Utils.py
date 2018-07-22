import json

from discord.ext import commands

from Util import GearbotLogging

bot = None

def on_ready(actual_bot):
    global bot
    bot = actual_bot


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
    await GearbotLogging.logToBotlog(f"Shutdown triggered by {trigger}.", log=True)
    await bot.logout()
    await bot.close()
    bot.aiosession.close()


def trim_message(message, limit):
    if len(message) < limit - 3:
        return message
    return f"{message[:limit-1]}..."


def clean(text):
    return text.replace("@","@\u200b").replace("`", "")

async def username(id):
    user = bot.get_user(id)
    if user is None:
        user = await bot.get_user_info(id)
    if user is None:
        return "UNKNOWN USER"
    return clean_user(user)

def clean_user(user):
    return f"{clean(user.name)}#{user.discriminator}"