import threading
import time

import discord

from Util import GearbotLogging
from commands.command import Command


class Test(Command):
    """Testing things"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Used for testing, only available in debug mode"

    def canExecute(self, user: discord.user.User) -> bool:
        import Variables
        return Variables.DEBUG_MODE

    async def execute(self, client, channel, user, params):
        await GearbotLogging.logToLogChannel("Initiating command")

        def otherThread():
            global MINECRAFT_TERMINATED, MINECRAFT_RUNNING
            # p = Popen(["D:\Minecraft\workspaces\modtester\gradlew.bat", "runClient"], cwd="D:\Minecraft\workspaces\modtester\\")
            # p = Popen(["~dev/modtester/gradlew.bat", "runClient"], cwd="~dev/modtester/")
            MINECRAFT_RUNNING = True
            # p.wait()
            time.sleep(10)
            MINECRAFT_TERMINATED = True
            print("minecraft terminated")

        thread = threading.Thread(target=otherThread)
        thread.start()
        return