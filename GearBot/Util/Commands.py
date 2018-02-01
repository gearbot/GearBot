import discord

import Variables
from commands.Clean import Clean
from commands.CustomCommands import AddCustomCommand, RemoveCustomCommand
from commands.Latest import Latest
from commands.Mute import Mute
from commands.OwnerCommands import Stop, Upgrade
from commands.Quote import Quote
from commands.RequestTesting import RequestTesting
from commands.Roles import Roles
from commands.SetInfo import SetInfo
from commands.Test import Test
from commands.Tester import Tester
from commands.command import Command
from commands.info import Info
from commands.ping import Ping


class Help(Command):
    """Shows help"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Shows a list of available commands or help for a specific command"
        self.extraHelp["Example usage"] = "!help\n!help <command>"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if len(params) > 0 and params[0] is not None:
            if params[0] in COMMANDS.keys():
                await COMMANDS[params[0]].sendHelp(client, channel)
            else :
                embed = discord.Embed(color=0x663399)
                embed.set_author(name="No info available")
                embed.description = "I'm sorry but i don't have any information available to display on that topic"
                await client.send_message(channel, embed=embed)
        else:
            embed = discord.Embed(colour=discord.Colour(0x663399))

            embed.set_author(name="Gearbot commands info")
            names = ""
            explanations = ""
            for key in COMMANDS:
                if COMMANDS[key].canExecute(user):
                    names += f"{key}\n"
                    explanations += f"{COMMANDS[key].__doc__}\n"
            embed.add_field(name="Basic commands", value=names)
            embed.add_field(name="\u200b", value=explanations)

            info = ""
            if len(Variables.CUSTOM_COMMANDS) > 0:
                for key in Variables.CUSTOM_COMMANDS:
                    info += f"{key}\n"
                embed.add_field(name="Custom commands", value=info, inline=False)

            await client.send_message(channel, embed=embed)


COMMANDS = {
    "ping": Ping(),
    "stop": Stop(),
    "upgrade": Upgrade(),
    "help": Help(),
    "add": AddCustomCommand(),
    "remove": RemoveCustomCommand(),
    "latest": Latest(),
    "test": Test(),
    "roles": Roles(),
    "tester": Tester(),
    "requesttesting": RequestTesting(),
    "clean": Clean(),
    "quote": Quote(),
    "info": Info(),
    "setinfo": SetInfo(),
    "mute": Mute()
}
