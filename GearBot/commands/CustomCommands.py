import discord

import Variables
from Util import Database
from commands.RoleCommands import RoleCommand


class AddCustomCommand(RoleCommand):
    """Adds a command"""

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if len(params) < 2:
            await self.sendHelp(client, channel)
        else:
            customCommands = getCommands(channel.server.id)
            if (Variables.CUSTOM_COMMANDS[channel.server.id].keys().__contains__(params[0])):
                await client.send_message(channel, "I already know this command, please remove it first if you want to replace it")
            else:
                text = " ".join(params[1::])
                Variables.CUSTOM_COMMANDS[channel.server.id][params[0].lower()] = text
                Database.executeStatement("INSERT INTO command (name, text, server) VALUES (%s, %s, %s)", (params[0], text, channel.server.id,))
                await client.send_message(channel, "Command added")



class RemoveCustomCommand(RoleCommand):
    """Removes a command"""

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        customCommands = getCommands(channel.server.id)
        if (customCommands.keys().__contains__(params[0])):
            del Variables.CUSTOM_COMMANDS[channel.server.id][params[0]]
            Database.executeStatement("DELETE FROM command WHERE name=%s AND server=%s", (params[0], channel.server.id))
            await client.send_message(channel, "Command removed")
        else:
            await client.send_message(channel, "I don't know that command so was unable to remove it")

def getCommands(serverID):
    if not serverID in Variables.CUSTOM_COMMANDS.keys():
        loadCommands(serverID)
    return Variables.CUSTOM_COMMANDS[serverID]


def loadCommands(serverID):
    Variables.CUSTOM_COMMANDS[serverID] = dict()

    db = Database.getConnection()
    cursor = db.cursor()
    cursor.execute(f"SELECT name, text FROM command WHERE server='{serverID}'")
    results = cursor.fetchall()
    for row in results:
        name = row[0]
        text = row[1]
        Variables.CUSTOM_COMMANDS[serverID][name] = text
    db.close()