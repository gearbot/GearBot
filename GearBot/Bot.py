import discord
import asyncio
import os

from GearBot.commands.ping import Ping
from GearBot.functions import configuration, protectedmessage, permissions, spam, customcommands
from tabulate import tabulate

client = discord.Client()
debugMode = None
info = None
prefix = "!" #TODO: move to config

commands = {
    "ping": Ping()
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
    global prefix
    global client
    info = []
    try:
        if (message.content.startswith(prefix)):
            info = message.content[1:].split()
            command = commands[info[0]]
            if (command is not None):
                if (command.canExecute(message.author)):
                    await command.execute(client, message.channel, message.author, info[1:])
                else:
                    await client.send_message(message.channel, "You do not have permission to execute this command")
            else:
                #custom commands check
    except discord.Forbidden as e:
        print("Exception: Bot is not allowed to send messages")
        onCommandError(message.channel, info[0], info[1:], e)
        pass
    except discord.InvalidArgument as e:
        onCommandError(message.channel, info[0], info[1:], e)
        print("Exception: Invalid message arguments")
        pass
    except Exception as e:
        onCommandError(message.channel, info[0], info[1:], e)
        print("Exception: {}".format(str(e)))
        pass

async def onCommandError(channel, name, info, exception):
    global client
    try:
        print("Command execution failed:")
        print("    Command: {}".format(name))
        print("    Arguments: {}".format(info))
        print("    Channel: {}".format(channel.name))
        print("    Server: {}".format(channel.server))
        print(exception)
        await client.send_message(channel, "Execution of the {} command failed, please try again later".format(name))
    except Exception as e:
        print("Failed to notify caller:")
        print(e)



try:
    token = os.environ['gearbotlogin']
except KeyError:
    token = input("Please enter your Discord token: ")
client.run(token)
