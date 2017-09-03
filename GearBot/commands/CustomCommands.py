from GearBot.commands.RoleCommands import RoleCommand
from GearBot.util import prefix

customCommands = dict()


class AddCustomCommand(RoleCommand):
    def __init__(self):
        super().__init__("Adds a command", "manage_commands")

    async def execute(self, client, channel, user, params):
        commands = getCommands(channel.server)
        if len(params) < 2:
            await client.send_message(channel, "Not enough params\nUsage: {}add <name> <text>".format(prefix))
        else:
            if (commands.keys().__contains__(params[0])):
                await client.send_message(channel, "I already know this command, please remove it first if you want to replace it")
            else:
                commands[params[0]] = " ".join(params[1::])
                await client.send_message(channel, "Command added")


class RemoveCustomCommand(RoleCommand):
    def __init__(self):
        super().__init__("Removes a command", "manage_commands")

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