import os
import traceback

import discord
import sys

from commands.OwnerCommands import Stop, Upgrade
from commands.command import Command
from commands import CustomCommands
from commands.ping import Ping
from commands.util import prefix
from functions import configuration, spam


class Help(Command):
    def __init__(self):
        super().__init__("Shows help")

    async def execute(self, client, channel, user, params):
        info = "**Available commands:**\n------------------------------------\n"
        for key in commands:
            if (commands[key].canExecute(user)):
                info += "{} : {}\n".format(key, commands[key].help)
        cCommands = CustomCommands.getCommands(channel.server)
        if (len(cCommands.keys())):
            info += "\n**Other commands:**\n------------------------------------\n"
            for key in cCommands:
                info += "{}\n".format(key)

        await client.send_message(channel, info)

client = discord.Client()

commands = {
    "ping": Ping(),
    "stop": Stop(),
    "upgrade": Upgrade(),
    "help": Help(),
    #"add": AddCustomCommand(),
    #"remove": RemoveCustomCommand()
}

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    print('Do not create custom commands that might interfere with the commands of other bots')
    print('You can report an Issue/Bug on the GearBot repository (https://github.com/AEnterprise/Gearbot)')
    print('This bot is made by Slak#9006 & AEnterprise#4693')
    print('------')

    for server in client.servers:
        if not configuration.hasconfig(server):
            configuration.createconfigserver(server, True)

    global info
    info = await client.application_info()
    global debugMode
    debugMode = (info.name == 'SlakBotTest') | (info.name == 'Parrot test')


@client.event
async def on_message(message):
    if (message.content is None) | (message.content == ''):
        return
    if (not message.content.startswith('!')) & (not message.channel.is_private):
        await        spam.check_for_spam(client, message)
    info = []
    try:
        if (message.content.startswith(prefix)):
            info = message.content[1:].split()
            if (commands.keys().__contains__(info[0])):
                command = commands[info[0]]
                if (command.canExecute(message.author)):
                    await command.execute(client, message.channel, message.author, info[1:])
                else:
                    await client.send_message(message.channel, "You do not have permission to execute this command")
            else:
                cCommands = CustomCommands.getCommands(message.channel.server)
                if (cCommands.keys().__contains__(info[0])):
                    await client.send_message(message.channel, cCommands[info[0]])
    except discord.Forbidden as e:
        print("Exception: Bot is not allowed to send messages")
        onCommandError(message.channel, info[0], info[1:], e)
        pass
    except discord.InvalidArgument as e:
        onCommandError(message.channel, info[0], info[1:], e)
        print("Exception: Invalid message arguments")
        pass
    except Exception as e:
        await onCommandError(message.channel, info[0], info[1:], e)
        traceback.print_exc()
        pass

async def onCommandError(channel, name, info, exception):
    global client
    try:
        print("Command execution failed:")
        print("    Command: {}".format(name))
        print("    Arguments: {}".format(info))
        print("    Channel: {}".format(channel.name))
        print("    Server: {}".format(channel.server))
        print("    Exception: {}".format(str(exception)))
        await client.send_message(channel, "Execution of the {} command failed, please try again later".format(name))
    except Exception as e:
        print("Failed to notify caller:")
        print(e)


if __name__ == '__main__':
    sys.stdout = open("log.txt", "w")
    sys.stderr = open("error.txt", "w")
    try:
        token = os.environ['gearbotlogin']
    except KeyError:
        token = input("Please enter your Discord token: ")
    client.run(token)