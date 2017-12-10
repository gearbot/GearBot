import discord

import Variables
from Util import configuration
from commands.RoleCommands import RoleCommand
from versions import VersionInfo


class AddVersion(RoleCommand):
    """Add a new BC release"""

    def __init__(self):
        super().__init__()
        self.extraHelp["params"] = "Minecraft version\nBuildcraft version\nDesignation\nBlog post link"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if not len(params) == 4:
            await client.send_message(channel, "Invalid params")
            return
        MCVersion = params[0]
        BCVersion = params[1]
        designation = params[2]
        blogLink = params[3]

        if not MCVersion in VersionInfo.versions.keys():
            VersionInfo.versions[MCVersion] = dict()
        VersionInfo.versions[MCVersion]["BC_VERSION"] = BCVersion
        VersionInfo.versions[MCVersion]["BLOG_LINK"] = blogLink
        VersionInfo.versions[MCVersion]["BC_DESIGNATION"] = designation
        VersionInfo.saveVersionInfo()
        Variables.AWAITING_REPLY_FROM = user.id
        Variables.NEW_PRIMARY_VERSION = VersionInfo.versions[MCVersion]
        await client.send_message(channel, f"Thanks for telling me about BuildCraft {BCVersion}, is this the current primary release?")
        return

    def onReady(self, client: discord.Client):
        self.role = configuration.getConfigVar("DEV_ROLE_ID")
        Variables.GENERAL_CHANNEL = client.get_channel(configuration.getConfigVar("GENERAL_CHANNEL", "0"))