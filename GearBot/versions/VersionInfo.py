import json

import discord

from Util import configuration
from commands.RoleCommands import RoleCommand

versions:dict = dict()

def initVersionInfo():
    try:
        with open('versions.json', 'r') as jsonfile:
            global versions
            versions = json.load(jsonfile)
    except FileNotFoundError:
        with open("versions.json", 'w') as jsonfile:
            initVersionInfo()
    except Exception as e:
        print(e)
        raise e


class addVersion(RoleCommand):
    """Adds a new BC release"""

    def __init__(self):
        super().__init__()
        self.extraHelp["params"] = "Minecraft version\nBuildcraft version\nBlog post link"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        global versions
        if not params == 3:
            await client.send_message(channel, "Invalid params")
            return
        if not params[0] in versions.keys():
            versions[params[0]] = dict()
            await client.send_message(channel, "I didn't know that MC version existed, yet, now i do!")
            return
        return

    def onReady(self, client: discord.Client):
        self.role = configuration.getConfigVar("DEV_ROLE_ID")