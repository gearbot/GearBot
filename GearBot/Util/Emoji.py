from discord import utils

from Util import Configuration

emojis = dict()

def on_ready(bot):
    for name, eid in Configuration.getMasterConfigVar("EMOJI").items():
        emojis[name] = utils.get(bot.emojis, id=eid)

def get_chat_emoji(name):
    emoji = emojis[name]
    return f"<:{emoji.name}:{emoji.id}>"