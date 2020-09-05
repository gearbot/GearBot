from discord import utils

from Util import Configuration

emojis = dict()

BACKUPS = {
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
    "ALTER": "🛠",
    "BAD_USER": "😶",
    "BAN": "🚪",
    "BEAN": "🌱",
    "BOOT": "👢",
    "BUG": "🐛",
    "CATEGORY": "📚",
    "CHANNEL": "📝",
    "CLOCK": "⏰",
    "CREATE": "🔨",
    "DELETE": "⛏",
    "DIAMOND": "⚙",
    "DND": "❤",
    "EDIT": "📝",
    "EYES": "👀",
    "GAMING": "🎮",
    "GOLD": "⚙",
    "IDLE": "💛",
    "INNOCENT": "😇",
    "IRON": "⚙",
    "JOIN": "📥",
    "LEAVE": "📤",
    "LEFT": "⬅️",
    "LOADING": "⏳",
    "LOCK": "🔒",
    "MUSIC": "🎵",
    "MUTE": "😶",
    "NAMETAG": "📛",
    "NICKTAG": "📛",
    "NO": "🚫",
    "OFFLINE": "💙",
    "ONLINE": "💚",
    "PIN": "📌",
    "QUESTION": "❓",
    "REFRESH": "🔁",
    "RIGHT": "➡️",
    "ROLE_ADD": "🛫",
    "ROLE_REMOVE": "🛬",
    "SEARCH": "🔎",
    "SINISTER": "😈",
    "SPY": "🕵",
    "STONE": "⚙",
    "STREAMING": "💜",
    "TACO": "🌮",
    "THINK": "🤔",
    "TODO": "📋",
    "TRASH": "🗑",
    "VOICE": "🔊",
    "WARNING": "⚠",
    "WATCHING": "📺",
    "WHAT": "☹",
    "WINK": "😉",
    "WOOD": "⚙",
    "WRENCH": "🔧",
    "YES": "✅"
}


async def initialize(bot):
    emoji_guild = await bot.fetch_guild(Configuration.get_master_var("EMOJI_GUILD"))
    for name, eid in Configuration.get_master_var("EMOJI", {}).items():
        emojis[name] = utils.get(bot.emojis, id=eid)


def get_chat_emoji(name):
    return str(get_emoji(name))


def get_emoji(name):
    if name in emojis:
        return emojis[name]
    else:
        return BACKUPS[name]
