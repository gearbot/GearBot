import discord

from Util import configuration
from commands.RoleCommands import RoleCommand
from versions import VersionInfo


class AddCompatVersion(RoleCommand):
    """Add a new BCC release"""

    def __init__(self):
        super().__init__()
        self.extraHelp["params"] = "Minecraft version\nBuildcraft Compat version\nBlog post link"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if not len(params) == 3:
            await client.send_message(channel, "Invalid params")
            return
        MCVersion = params[0]
        BCCVersion = params[1]
        blogLink = params[2]

        if not MCVersion in VersionInfo.versions.keys():
            VersionInfo.versions[MCVersion] = dict()
        VersionInfo.versions[MCVersion]["BCC_VERSION"] = BCCVersion
        VersionInfo.versions[MCVersion]["BCC_BLOG_LINK"] = blogLink
        VersionInfo.saveVersionInfo()
        await client.send_message(channel, f"Thanks for telling me about BuildCraft Compat {BCCVersion}")
        return

    def onReady(self, client: discord.Client):
        self.role = configuration.getConfigVar("DEV_ROLE_ID")