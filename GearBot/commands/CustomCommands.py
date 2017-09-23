import json
import logging

import simplejson

from commands.RoleCommands import RoleCommand

customCommands = dict()


class AddCustomCommand(RoleCommand):
    def __init__(self):
        super().__init__("Adds a command", extrahelp="Adds a custom command\nUsage: !add <name> <text>")

    async def execute(self, client, channel, user, params):
        commands = getCommands(channel.server)
        if len(params) < 2:
            await self.sendHelp(client, channel)
        else:
            if (commands.keys().__contains__(params[0])):
                await client.send_message(channel, "I already know this command, please remove it first if you want to replace it")
            else:
                commands[params[0].lower()] = " ".join(params[1::])
                await client.send_message(channel, "Command added")
                with open('commands.json', 'w') as jsonfile:
                    jsonfile.write((simplejson.dumps(customCommands, indent=4, skipkeys=True, sort_keys=True)))
                    jsonfile.close()


class RemoveCustomCommand(RoleCommand):
    def __init__(self):
        super().__init__("Removes a command", extrahelp="Usage: !remove <name>")

    async def execute(self, client, channel, user, params):
        commands = getCommands(channel.server)
        if (commands.keys().__contains__(params[0])):
            del commands[params[0]]
            await client.send_message(channel, "Command removed")
        else:
            await client.send_message(channel, "I don't know that command so was unable to remove it")

def getCommands(server):
    if not customCommands.keys().__contains__(server.id):
        customCommands[server.id] = dict()
    return customCommands[server.id]

def loadCommands():
    try:
        jsonfile = open('commands.json', 'r')
        global customCommands
        customCommands = json.load(jsonfile)
        jsonfile.close()
    except FileNotFoundError:
        logging.warning("Unable to load custom commands, file not found")