import json
import logging

import discord

import Util
import Variables
from commands.RoleCommands import RoleCommand


class AddCustomCommand(RoleCommand):
    """Adds a command"""

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if len(params) < 2:
            await self.sendHelp(client, channel)
        else:
            if Variables.CUSTOM_COMMANDS.keys().__contains__(params[0]):
                await client.send_message(channel, "I already know this command, please remove it first if you want to replace it")
            else:
                text = " ".join(params[1::])
                Variables.CUSTOM_COMMANDS[params[0].lower()] = text
                saveCommands()
                await client.send_message(channel, "Command added")



class RemoveCustomCommand(RoleCommand):
    """Removes a command"""

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if (Variables.CUSTOM_COMMANDS.keys().__contains__(params[0])):
            del Variables.CUSTOM_COMMANDS[params[0]]
            saveCommands()
            await client.send_message(channel, "Command removed")
        else:
            await client.send_message(channel, "I don't know that command so was unable to remove it")


async def loadCommands():
    logging.info("Loading custom commands")
    try:
        with open('commands.json', 'r') as jsonfile:
            Variables.CUSTOM_COMMANDS = json.load(jsonfile)
    except FileNotFoundError:
        await Util.GearbotLogging.logToLogChannel("No custom commands file found")
    except Exception as e:
        await Util.GearbotLogging.logToLogChannel("Error parsing custom commands")
        print(e)
        raise e


def saveCommands():
    with open('commands.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(Variables.CUSTOM_COMMANDS, indent=4, skipkeys=True, sort_keys=True)))