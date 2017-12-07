import threading
import time
from itertools import combinations

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

    count = 0
    list = ["builders", "energy", "factory", "robotics", "silicon", "transport"]
    for i in range(1, len(list)):
        for combo in combinations(list, i):
            print(combo)
            count += 1
    print(f"total combinations: {count}")