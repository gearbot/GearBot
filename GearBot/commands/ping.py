import time

import discord

import Variables
from commands.command import Command


class Ping(Command):
    """Basic ping"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Just pongs"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if canGetTimings(user):
            t1 = time.perf_counter()
            await client.send_typing(channel)
            t2 = time.perf_counter()
            await client.send_message(channel, f":hourglass: Gateway ping is {round((t2 - t1) * 1000)}ms :hourglass:")
        else:
            await (client.send_message(channel, "Yes i'm still here, thanks caring random user! <:winkTank:393823997076307979>"))

def canGetTimings(user):
    if user.roles is None:
        return False
    for role in user.roles:
        if role.id == "346629002561060864":
            return True
    if Variables.DEBUG_MODE or user.id == Variables.APP_INFO.owner.id:
        return True