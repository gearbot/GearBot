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
    "10": "🔟"
}


def on_ready(bot):
    for name, eid in Configuration.getMasterConfigVar("EMOJI", {}).items():
        emojis[name] = utils.get(bot.emojis, id=eid)


def get_chat_emoji(name):
    if name in emojis:
        emoji = emojis[name]
        return f"<:{emoji.name}:{emoji.id}>"
    else:
        return BACKUPS[name]


def get_emoji(name):
    if name in emojis:
        return emojis[name]
    else:
        return BACKUPS[name]
