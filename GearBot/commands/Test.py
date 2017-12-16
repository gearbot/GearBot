import asyncio
import datetime
import os
import shutil
import threading
import time
import traceback
from itertools import combinations
from subprocess import Popen

import discord

from commands.command import Command


class Test(Command):
    """Testing things"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Used for testing, only available in debug mode"

    def canExecute(self, user: discord.user.User) -> bool:
        import Variables
        return Variables.DEBUG_MODE or user.id == Variables.APP_INFO.owner.id

    async def execute(self, client:discord.Client, channel:discord.Channel, user:discord.user.User, params)-> None:
        await client.send_message(channel, "Initiating...")
        t = threading.Thread(target=runTest, args=(client, channel,client.loop,))
        t.start()

        return

        count = 0
        list = ["builders", "energy", "factory", "robotics", "silicon", "transport"]
        for i in range(1, len(list)):
            for combo in combinations(list, i):
                print(combo)
                count += 1
        print(f"total combinations: {count}")

def runTest(client:discord.Client, channel:discord.Channel, clientLoop):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(runTestAsync(client, channel, clientLoop))
    loop.close()

async def runTestAsync(client:discord.Client, channel:discord.Channel, clientLoop):
    try:
        gearbox = os.getcwd() + "\\\\gearbox"
        if not os.path.exists(gearbox):
            os.makedirs(gearbox)
        else:
            shutil.rmtree(gearbox + "\\\\BuildCraft")
        runCommand(["git", "clone", "https://github.com/BuildCraft/BuildCraft"])
        props = {}
        embed = discord.Embed(title="Extracted information")
        with open(gearbox + "\\\\BuildCraft\\\\build.properties", "r") as file:
            lines = file.readlines()
            for line in lines:
                line = line.strip()
                if line:
                    kv = line.split("=")
                    props[kv[0]] = kv[1]
                    embed.add_field(name=kv[0], value=kv[1])
        asyncio.run_coroutine_threadsafe(client.send_message(channel, "Clone complete", embed=embed), clientLoop)

        runCommand(["git", "submodule", "init"], folder="BuildCraft")
        runCommand(["git", "submodule", "update"], folder="BuildCraft")
        asyncio.run_coroutine_threadsafe(client.send_message(channel, "Submodules ready"), clientLoop)
        runCommand(["gradlew.bat", "build", "--no-daemon"], folder="BuildCraft", prepend=True)
        with open(f"{gearbox}\\\\BuildCraft\\\\build\\\\libs\\\\{props['mod_version']}\\\\buildcraft-{props['mod_version']}.jar", "rb") as jar:
            asyncio.run_coroutine_threadsafe(client.send_file(channel, jar, content="Done"), clientLoop)
        forgelink = "http://files.minecraftforge.net/maven/net/minecraftforge/forge/1.12.2-14.23.1.2566/forge-1.12.2-14.23.1.2566-installer.jar"
    except Exception as e:
        embed = discord.Embed(colour=discord.Colour(0xff0000),
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))

        embed.set_author(name="Something went wrong!")
        embed.add_field(name="Exception", value=e)
        embed.add_field(name="Stacktrace", value=traceback.format_exc())
        asyncio.run_coroutine_threadsafe(client.send_message(channel, embed=embed), clientLoop)

def runCommand(command, folder=None, delay=1, prepend=False):
    location = os.getcwd() + "\\\\gearbox"
    if not folder is None:
        location += f"\\\\{folder}"
    if prepend:
        command[0] =  f"{location}\\\\{command[0]}"
    p = Popen(command, cwd=location)
    while p.poll() is None:
        time.sleep(delay)
    p.communicate()
    code = p.returncode
    return code