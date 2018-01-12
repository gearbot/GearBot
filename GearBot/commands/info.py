import datetime
import time

import discord

from commands.command import Command
from versions import VersionChecker, VersionInfo


class Info(Command):
    """Version info"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Gives info about releases"
        self.extraHelp["example usage"] = f"!info {VersionInfo.getLatest(VersionChecker.BC_VERSION_LIST)}"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if len(params) == 0:
            await client.send_message(channel, "I'm sorry i'm an expert on gears and BuildCraft releases, not a creepy mind reading bot (yet), please try telling me what version you want more info about")
            return
        v = params[0]
        if not (v in VersionChecker.BC_VERSION_LIST.keys() or v in VersionChecker.BCC_VERSION_LIST.keys() or v in VersionChecker.BCT_VERSION_LIST.keys()):
            await client.send_message(channel, "I'm sorry but even with all my gears i can't seem to find that version, are you sure it exists?")
        else:
            embed = discord.Embed(title=f"Results for {v}:", color=0xDDDDDD, timestamp=datetime.datetime.utcfromtimestamp(time.time()))
            embed.set_thumbnail(url="https://i.imgur.com/IKRpy3l.png")
            if v in VersionChecker.BC_VERSION_LIST.keys():
                BCv = VersionChecker.BC_VERSION_LIST[v]
                info = ""
                for key, value in BCv.items():
                    info = info + f"{'download' if key == 'downloads' else key}: {value['main'] if key == 'downloads' else value}\n"
                embed.add_field(name=f"BuildCraft {v}", value=f"{info}\n\u200b")
            if v in VersionChecker.BCC_VERSION_LIST.keys():
                BCCv = VersionChecker.BCC_VERSION_LIST[v]
                info = ""
                for key, value in BCCv.items():
                    info = info + f"{'download' if key == 'downloads' else key}: {value['main'] if key == 'downloads' else value}\n"
                embed.add_field(name=f"BuildCraft Compat {v}", value=f"{info}\n\u200b")
            if v in VersionChecker.BCT_VERSION_LIST.keys():
                BCTv = VersionChecker.BCT_VERSION_LIST[v]
                info = ""
                for key, value in BCTv.items():
                    info = info + f"{'download' if key == 'downloads' else key}: {value['main'] if key == 'downloads' else value}\n"
                embed.add_field(name=f"Buildcraft Test {v}", value=f"{info}\n\u200b")
            await client.send_message(channel, embed=embed)