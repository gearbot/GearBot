import discord
import math
import Variables
from commands.CustomCommands import AddCustomCommand, RemoveCustomCommand
from commands.Latest import Latest
from commands.OwnerCommands import Stop, Upgrade
from commands.Test import Test
from commands.command import Command
from commands.ping import Ping


class Help(Command):
    """Shows help"""

    Command.extraHelp["info"] = "Shows a list of available commands or help for a specific command"
    Command.extraHelp["Example usage"] = "!help\n!help <command>"


    async def execute(self, client, channel, user, params):
        if len(params) > 0 and params[0] is not None and params[0] in COMMANDS.keys():
            await COMMANDS[params[0]].sendHelp(client, channel)
        else:
            embed = discord.Embed(colour=discord.Colour(0x663399))

            embed.set_author(name="Gearbot commands info")
            info = ""
            for key in COMMANDS:
                if COMMANDS[key].canExecute(user):
                    info += f"{key}"
                    for i in range(0, (20 - key.__len__())):
                        info += " "
                    info += f"{COMMANDS[key].__doc__}\n"
            embed.add_field(name="Basic commands", value=info)

            info = ""

            for key in Variables.CUSTOM_COMMANDS:
                info += f"{key}\n"
            embed.add_field(name="custom commands", value=info, inline=False)

            await client.send_message(channel, embed=embed)


COMMANDS = {
    "ping": Ping(),
    "stop": Stop(),
    "upgrade": Upgrade(),
    "help": Help(),
    "add": AddCustomCommand(),
    "remove": RemoveCustomCommand(),
    "latest": Latest(),
    "test": Test()
}
