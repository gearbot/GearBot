import json
import logging
import Variables

from commands.RoleCommands import RoleCommand



class AddCustomCommand(RoleCommand):
    """Adds a command"""

    async def execute(self, client, channel, user, params):
        if len(params) < 2:
            await self.sendHelp(client, channel)
        else:
            if (Variables.CUSTOM_COMMANDS.keys().__contains__(params[0])):
                await client.send_message(channel, "I already know this command, please remove it first if you want to replace it")
            else:
                Variables.CUSTOM_COMMANDS[params[0].lower()] = " ".join(params[1::])
                await client.send_message(channel, "Command added")
                with open('commands.json', 'w') as jsonfile:
                    jsonfile.write((json.dumps(Variables.CUSTOM_COMMANDS, indent=4, skipkeys=True, sort_keys=True)))
                    jsonfile.close()


class RemoveCustomCommand(RoleCommand):
    """Removes a command"""

    async def execute(self, client, channel, user, params):
        if (Variables.CUSTOM_COMMANDS.keys().__contains__(params[0])):
            del Variables.CUSTOM_COMMANDS[params[0]]
            await client.send_message(channel, "Command removed")
        else:
            await client.send_message(channel, "I don't know that command so was unable to remove it")

def loadCommands():
    try:
        with open('commands.json', 'r') as jsonfile:
            Variables.CUSTOM_COMMANDS = json.load(jsonfile)
    except FileNotFoundError:
        logging.warning("Unable to load custom commands, file not found")