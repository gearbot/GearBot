from discord import utils

from Util import Configuration

emojis = dict()

BACKUPS = {
    "INNOCENT": "😇",
    "JOIN": "📥",
    "LEAVE": "📤",
    "LEFT": "◀",
    "LOADING": "⏳",
    "MUTE": "😶",
    "NAMETAG": "📛",
    "NICKTAG": "📛",
    "NO": "🚫",
    "REFRESH": "🔁",
    "RIGHT": "▶",
    "WARNING": "⚠",
    "WHAT": "☹",
    "YES": "✅",
    "DIAMOND": "⚙",
    "GOLD": "⚙",
    "IRON": "⚙",
    "STONE": "⚙",
    "WOOD": "⚙",
    "TODO": "📋",
    "TACO": "🌮",
    "WRENCH": "🔧",
    "1": "1⃣",
    "2": "2⃣",
    "3": "3⃣",
    "4": "4⃣",
    "5": "5⃣",
    "6": "6⃣",
    "7": "7⃣",
    "8": "8⃣",
    "9": "9⃣",
    "10": "🔟",
    "ROLE_ADD": "🛫",
    "ROLE_REMOVE": "🛬",
    "CREATE": "🔨",
    "ALTER": "🛠",
    "DELETE": "⛏",
    "VOICE": "🔊",
    "EYES": "👀",
    "SPY": "🕵",
    "QUESTION": "❓",
    "CLOCK": "⏰",
    "SINISTER": "😈",
    "THINK": "🤔",
    "WINK": "😉",
    "ONLINE": "💚",
    "IDLE": "💛",
    "DND": "❤",
    "OFFLINE": "💙",
    "STREAMING": "💜",
    "SEARCH": "🔎"
}


def initialize(bot):
    for name, eid in Configuration.get_master_var("EMOJI", {}).items():
        emojis[name] = utils.get(bot.emojis, id=eid)


def get_chat_emoji(name):
    return str(get_emoji(name))


def get_emoji(name):
    if name in emojis:
        return emojis[name]
    else:
        return BACKUPS[name]
