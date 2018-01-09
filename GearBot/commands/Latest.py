import datetime
import time

import discord

from commands.command import Command
from versions import VersionInfo, VersionChecker


class Latest(Command):
    """Info about the latest releases"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Displays the latest versions for the latest MC versions and their blog/download links"

    async def execute(self, client, channel, user, params):

        if len(params) == 1:
            v = params[0]
            embed = discord.Embed(title=f"Buildcraft releases",
                                  url="http://www.mod-buildcraft.com/",
                                  colour=discord.Colour(0x54d5ff),
                                  timestamp=datetime.datetime.utcfromtimestamp(time.time()))
            embed.set_thumbnail(url="https://i.imgur.com/YKGkDDZ.png")

            if v in VersionChecker.VERSIONS_PER_MC_VERSION:
                mc_version = VersionChecker.VERSIONS_PER_MC_VERSION[v]
                latest_bc_v = VersionInfo.getLatestArray(mc_version['BC'])
                latest_bc = VersionChecker.BC_VERSION_LIST[latest_bc_v]
                latest_bcc_v = VersionInfo.getLatestArray(mc_version['BCC'])


                info = f"Buildcraft {latest_bc_v}\n[Changelog](https://www.mod-buildcraft.com/pages/buildinfo/BuildCraft/changelog/{latest_bc_v}.html) | [Blog]({latest_bc['blog_entry'] if 'blog_entry' in latest_bc else 'https://www.mod-buildcraft.com'}) | [Direct download]({latest_bc['downloads']['main']})"
                if "supported" in latest_bc.keys() and latest_bc["supported"] == False:
                    info = info + " | **THIS VERSION IS UNSUPPORTED**"
                info = info + "\n\n\u200b"
                if not latest_bcc_v is None:
                    latest_bcc = VersionChecker.BC_VERSION_LIST[latest_bcc_v]
                    info += f"Buildcraft Compat {latest_bcc_v}\n[Blog]({latest_bcc['blog_entry'] if 'blog_entry' in latest_bcc else 'https://www.mod-buildcraft.com'}) | [Direct download]({latest_bcc['downloads']['main']})"
                    if "supported" in latest_bcc.keys() and latest_bcc["supported"] == False:
                        info = info + " | **THIS VERSION IS UNSUPPORTED**"
                    info = info + "\n\n\u200b"
                embed.add_field(name=f"Latest BuildCraft releases for {v}:",
                                value=info)
                await client.send_message(channel, embed=embed)
            else:
                await client.send_message(channel, f"I'm sorry but there seem to be no releases for {v}, if they exist they are probably so old i can't make out their labels anymore")

        else:
            latest = VersionInfo.getLatest(VersionChecker.BC_VERSION_LIST)
            embed = discord.Embed(title=f"The latest version of BuildCraft is {latest}",
                                  colour=discord.Colour(0x54d5ff),
                                  url=VersionChecker.BC_VERSION_LIST[latest]["blog_entry"],
                                  description="Latest versions per MC version:",
                                  timestamp=datetime.datetime.utcfromtimestamp(time.time()))
            embed.set_thumbnail(url="https://i.imgur.com/YKGkDDZ.png")
            embed.set_author(name="Buildcraft releases", url="http://www.mod-buildcraft.com/")
            count = 0
            for v in VersionInfo.getSortedVersions(VersionChecker.VERSIONS_PER_MC_VERSION):
                mc_version = VersionChecker.VERSIONS_PER_MC_VERSION[v]
                latest_bc_v = VersionInfo.getLatestArray(mc_version['BC'])
                latest_bc = VersionChecker.BC_VERSION_LIST[latest_bc_v]
                latest_bcc_v = VersionInfo.getLatestArray(mc_version['BCC'])
                if "supported" in latest_bc.keys() and latest_bc["supported"] == False:
                    continue

                info = f"Buildcraft {latest_bc_v}\n[Changelog](https://www.mod-buildcraft.com/pages/buildinfo/BuildCraft/changelog/{latest_bc_v}.html) | [Blog]({latest_bc['blog_entry']}) | [Direct download]({latest_bc['downloads']['main']})\n\n\u200b"
                if not latest_bcc_v is None:
                        latest_bcc = VersionChecker.BC_VERSION_LIST[latest_bcc_v]
                        info += f"Buildcraft Compat {latest_bcc_v}\n[Blog]({latest_bcc['blog_entry']}) | [Direct download]({latest_bcc['downloads']['main']})\n\n\u200b"
                embed.add_field(name=v,
                            value=info)
                count = count + 1
                if count == 3:
                    break

            embed.add_field(name="Older versions",
                            value="All other Buildcraft versions can be found in the [archives](https://www.mod-buildcraft.com/releases/)")


            await client.send_message(channel, embed=embed)