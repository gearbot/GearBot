import datetime
import time

import discord

from commands.command import Command


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

        embed = discord.Embed(title="The latest version of BuildCraft is 7.99.12", colour=discord.Colour(0x54d5ff),
                              url="https://www.mod-buildcraft.com/buildcraft-79912-alpha-buildcraft-79981-alpha-buildcraft-7123-stable-buildcraftcompat-717-stable-buildcraftcompat-7990-alpha.html",
                              description="Latest versions per MC version:",
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))

        embed.set_thumbnail(url="https://i.imgur.com/YKGkDDZ.png")
        embed.set_author(name="Buildcraft releases", url="http://www.mod-buildcraft.com/")

        embed.add_field(name="1.12.2",
                        value="Buildcraft 7.99.12 (alpha)\n[Blog](https://www.mod-buildcraft.com/buildcraft-79912-alpha-buildcraft-79981-alpha-buildcraft-7123-stable-buildcraftcompat-717-stable-buildcraftcompat-7990-alpha.html) | [Direct download](https://www.mod-buildcraft.com/releases/BuildCraft/7.99.12/buildcraft-7.99.12.jar)")

        embed.add_field(name="1.11.2",
                        value="Buildcraft 7.99.8.1 (alpha)\n[Blog](https://www.mod-buildcraft.com/buildcraft-79912-alpha-buildcraft-79981-alpha-buildcraft-7123-stable-buildcraftcompat-717-stable-buildcraftcompat-7990-alpha.html) | [Direct download](https://www.mod-buildcraft.com/releases/BuildCraft/7.99.8.1/buildcraft-7.99.8.1.jar)\n\nBuildcraft Compat 7.99.0\n[Blog](https://www.mod-buildcraft.com/buildcraft-79912-alpha-buildcraft-79981-alpha-buildcraft-7123-stable-buildcraftcompat-717-stable-buildcraftcompat-7990-alpha.html) | [Direct download](http://www.mod-buildcraft.com/releases/BuildCraftCompat/7.99.0/buildcraft-compat-7.99.0.jar)")
        embed.add_field(name="1.7.10",
                        value="Buildcraft 7.1.23 (stable)\n[Blog](https://www.mod-buildcraft.com/buildcraft-79912-alpha-buildcraft-79981-alpha-buildcraft-7123-stable-buildcraftcompat-717-stable-buildcraftcompat-7990-alpha.html) | [Direct download](https://www.mod-buildcraft.com/releases/BuildCraft/7.1.23/buildcraft-7.1.23.jar)\n\nBuildcraft Compat 7.1.7\n[Blog](https://www.mod-buildcraft.com/buildcraft-79912-alpha-buildcraft-79981-alpha-buildcraft-7123-stable-buildcraftcompat-717-stable-buildcraftcompat-7990-alpha.html) | [Direct download](http://www.mod-buildcraft.com/releases/BuildCraftCompat/7.1.7/buildcraft-compat-7.1.7.jar)")
        embed.add_field(name="Older versions",
                        value="All other Buildcraft versions can be found in the [archives](https://www.mod-buildcraft.com/releases/)")

        await client.send_message(channel, "The latest version of BuildCraft is 7.99.12 and can be found at <https://www.mod-buildcraft.com/buildcraft-79912-alpha-buildcraft-79981-alpha-buildcraft-7123-stable-buildcraftcompat-717-stable-buildcraftcompat-7990-alpha.html>", embed=embed)