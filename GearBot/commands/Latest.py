import datetime
import time

import discord

from commands.command import Command
from versions import VersionInfo


class Latest(Command):
    """Info about the latest releases"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Displays the latest versions for the latest MC versions and their blog/download links"

    async def execute(self, client, channel, user, params):
        # {
        #     "content": "The latest version of BuildCraft is 7.99.7 and can be found at <https://mod-buildcraft.com/buildcraft-7997-alpha.html>",
        #     "embed": {
        #         "title": "The latest version of BuildCraft is 7.99.7",
        #         "description": "Latest versions per MC version:",
        #         "url": "https://mod-buildcraft.com/buildcraft-7997-alpha.html",
        #         "color": 5559807,
        #         "timestamp": "2017-09-19T14:52:43.464Z",
        #
        #         "thumbnail": {
        #             "url": "https://i.imgur.com/YKGkDDZ.png"
        #         },
        #         "author": {
        #             "name": "Buildcraft releases",
        #             "url": "http://www.mod-buildcraft.com/"
        #         },
        #         "fields": [
        #             {
        #                 "name": "1.11.2",
        #                 "value": "Buildcraft 7.99.7 (alpha)\n[Blog](https://mod-buildcraft.com/buildcraft-7997-alpha.html) | [Direct download](https://www.mod-buildcraft.com/releases/BuildCraft/7.99.7/buildcraft-7.99.7.jar)"
        #             },
        #             {
        #                 "name": "1.7.10",
        #                 "value": "Buildcraft 7.1.22 (stable)\n[Blog](https://www.mod-buildcraft.com/buildcraft-7994-alpha-7122-stable.html) | [Direct download](https://www.mod-buildcraft.com/releases/BuildCraft/7.1.22/buildcraft-7.1.22.jar)\n\nBuildcraft Compat 7.1.6\n[Blog](https://www.mod-buildcraft.com/buildcraft-7120-compat-716.html) | [Direct download](http://www.mod-buildcraft.com/releases/BuildCraftCompat/7.1.6/buildcraft-compat-7.1.6.jar)"
        #             },
        #             {
        #                 "name": "Older versions",
        #                 "value": "All other Buildcraft versions can be found in the [archives](https://www.mod-buildcraft.com/releases/)"
        #             }
        #         ]
        #     }
        # }

        latest = VersionInfo.versions[VersionInfo.getSortedVersions()[0]]
        embed = discord.Embed(title=f"The latest version of BuildCraft is {latest['BC_VERSION']}", colour=discord.Colour(0x54d5ff),
                              url=latest["BLOG_LINK"],
                              description="Latest versions per MC version:",
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))
        embed.set_thumbnail(url="https://i.imgur.com/YKGkDDZ.png")
        embed.set_author(name="Buildcraft releases", url="http://www.mod-buildcraft.com/")
        for v in VersionInfo.getSortedVersions()[:3]:
            version = VersionInfo.versions[v]
            info = f"Buildcraft {version['BC_VERSION']} ({version['BC_DESIGNATION']})\n[Blog]({version['BLOG_LINK']}) | [Direct download](https://www.mod-buildcraft.com/releases/BuildCraft/{version['BC_VERSION']}/buildcraft-{version['BC_VERSION']}.jar)"
            if "BCC_VERSION" in version.keys():
                    info += f"\n\nBuildcraft Compat {version['BCC_VERSION']}\n[Blog]({version['BCC_BLOG_LINK']}) | [Direct download](https://www.mod-buildcraft.com/releases/BuildCraftCompat/{version['BCC_VERSION']}/buildcraft-compat-{version['BCC_VERSION']}.jar)"
            embed.add_field(name=v,
                        value=info)

        embed.add_field(name="Older versions",
                        value="All other Buildcraft versions can be found in the [archives](https://www.mod-buildcraft.com/releases/)")

        await client.send_message(channel, embed=embed)