from commands.CustomCommands import *
from commands.Latest import Latest
from commands.OwnerCommands import Stop, Upgrade
from commands.command import Command
from commands.ping import Ping


class Help(Command):
    def __init__(self):
        super().__init__("Shows help", extrahelp="Shows a list of available commands or help for a specific command")

    async def execute(self, client, channel, user, params):
        if len(params) > 0 and params[0] is not None and params[0] in COMMANDS.keys():
            COMMANDS[params[0]].sendHelp(client, channel)
        else:
            inf = "**Available commands:**\n------------------------------------\n"
            for key in COMMANDS:
                if COMMANDS[key].canExecute(user):
                    inf += f"{key} : {COMMANDS[key].help}\n"
            custom_commands = getCommands(channel.server)
            if len(custom_commands.keys()):
                inf += "\n**Other commands:**\n------------------------------------\n"
                for key in custom_commands:
                    inf += f"{key}\n"

            await client.send_message(channel, inf)

COMMANDS = {
    "ping": Ping(),
    "stop": Stop(),
    "upgrade": Upgrade(),
    "help": Help(),
    "add": AddCustomCommand(),
    "remove": RemoveCustomCommand(),
    "latest": Latest()
}

