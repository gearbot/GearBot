from discord import utils

from Util import Configuration

emojis = dict()

BACKUPS= {
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
        "TODO": "📋"
    }
def on_ready(bot):
    for name, eid in Configuration.getMasterConfigVar("EMOJI").items():
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