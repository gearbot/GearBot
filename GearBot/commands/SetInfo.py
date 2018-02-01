import discord

import Variables
from Util import configuration
from commands.RoleCommands import RoleCommand
from versions import VersionChecker


class SetInfo(RoleCommand):
    """Sets an info message for a (pre) release"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Allows setting a message on an announcement of a (pre-)release"
        self.extraHelp["params"] = "Type: the type of release (BC, BCC, BCT or BCCT)\nversion: The version to set the message for\nMessage: the rest of the command string will be used as message to set"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if len(params) < 3:
            await client.send_message(channel, "Please provide me with a release type, version and message")
            return
        info, targetChannel = getInfo(params[0], params[1])
        if info is None:
            await client.send_message(channel, f"I'm sorry but there is no trace of {params[0]} {params[1]} in my archives")
            return
        if not 'messageID' in info.keys():
            await client.send_message(channel, f"{params[1]} seems to predate my version checking so i can't set a message for it")
            return
        message = await client.get_message(targetChannel, info['messageID'])
        newMessage = ""
        if message.content.startswith(f"<@&{configuration.getConfigVar('TESTER_ROLE_ID')}>"):
            newMessage = f"<@&{configuration.getConfigVar('TESTER_ROLE_ID')}> "
        newMessage = newMessage + " ".join(params[2::])
        await client.edit_message(message, newMessage)
        await client.send_message(channel, "Info updated!")

    async def onReady(self, client: discord.Client):
        self.role = configuration.getConfigVar("DEV_ROLE_ID")


def getInfo(type, target):
    if type == 'BC':
        if target in VersionChecker.BC_VERSION_LIST.keys():
            return VersionChecker.BC_VERSION_LIST[target], Variables.ANNOUNCEMENTS_CHANNEL
    if type == 'BCC':
        if target in VersionChecker.BCC_VERSION_LIST.keys():
            return VersionChecker.BCC_VERSION_LIST[target], Variables.ANNOUNCEMENTS_CHANNEL
    if type == 'BCT':
        if target in VersionChecker.BCT_VERSION_LIST.keys():
            return VersionChecker.BCT_VERSION_LIST[target], Variables.TESTING_CHANNEL
    if type == 'BCCT':
        if target in VersionChecker.BCCT_VERSION_LIST.keys():
            return VersionChecker.BCCT_VERSION_LIST[target], Variables.TESTING_CHANNEL
    return None, None

