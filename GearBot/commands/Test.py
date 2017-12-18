import asyncio
import datetime
import logging
import os
import shutil
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
        self.extraHelp["info"] = "Used for testing only"

    def canExecute(self, user: discord.user.User) -> bool:
        import Variables
        return Variables.DEBUG_MODE or user.id == Variables.APP_INFO.owner.id

    async def execute(self, client:discord.Client, channel:discord.Channel, user:discord.user.User, params)-> None:
        await client.send_message(channel, "Initiating...")

        client.loop.create_task(runRealTest(client, channel))

        return

        count = 0
        list = ["builders", "energy", "factory", "robotics", "silicon", "transport"]
        for i in range(1, len(list)):
            for combo in combinations(list, i):
                print(combo)
                count += 1
        print(f"total combinations: {count}")

async def runRealTest(client:discord.Client, channel:discord.Channel):
    try:
        gearbox = os.getcwd() + r"\gearbox"
        if not os.path.exists(gearbox):
            os.makedirs(gearbox)
        else:
            shutil.rmtree(r"gearbox\BuildCraft")
        await runCommand(["git", "clone", "--depth=1","https://github.com/BuildCraft/BuildCraft"], shell=True)
        props = {}
        embed = discord.Embed(title="Extracted information")
        with open(gearbox + r"\BuildCraft\build.properties", "r") as file:
            lines = file.readlines()
            for line in lines:
                line = line.strip()
                if line:
                    kv = line.split("=")
                    props[kv[0]] = kv[1]
                    embed.add_field(name=kv[0], value=kv[1])
        await client.send_message(channel, "Clone complete", embed=embed)

        await runCommand(["git", "submodule", "init"], folder="BuildCraft", shell=True)
        await runCommand(["git", "submodule", "update"], folder="BuildCraft", shell=True)
        await client.send_message(channel, "Submodules ready")
        commands = []
        compileP = Popen([rf"{os.getcwd()}\gearbox\BuildCraft\gradlew.bat", "build", "--no-daemon"], cwd=rf"{os.getcwd()}\gearbox\BuildCraft")

        await runCommand(["wget", f"http://files.minecraftforge.net/maven/net/minecraftforge/forge/{props['mc_version']}-{props['forge_version']}/forge-{props['mc_version']}-{props['forge_version']}-installer.jar"], shell=True)
        while compileP.poll() is None:
            await asyncio.sleep(2)
        await client.send_file(channel, rf"{gearbox}\BuildCraft\build\libs\{props['mod_version']}\buildcraft-{props['mod_version']}.jar", content="Done")
    except Exception as e:
        logging.error(e)
        logging.error(traceback.format_exc())
        embed = discord.Embed(colour=discord.Colour(0xff0000),
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))

        embed.set_author(name="Something went wrong!")
        embed.add_field(name="Exception", value=e)
        embed.add_field(name="Stacktrace", value=traceback.format_exc())
        await client.send_message(channel, embed=embed)


async def runCommand(command, folder=None, delay=2, prepend=False, shell = False):
    location = os.getcwd() + r"\gearbox"
    if not folder is None:
        location += rf"\{folder}"
    if prepend:
        command[0] = rf"{location}\{command[0]}"
    p = Popen(command, cwd=location, shell=shell)
    while p.poll() is None:
        await asyncio.sleep(delay)
    p.communicate()
    code = p.returncode
    return code
