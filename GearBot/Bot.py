import json
import os
import traceback
from argparse import ArgumentParser
import logging
from logging import DEBUG, INFO, WARNING, ERROR

import discord

from commands.CustomCommands import RemoveCustomCommand, AddCustomCommand, customCommands
from commands.OwnerCommands import Stop, Upgrade
from commands.command import Command
from commands import CustomCommands
from commands.ping import Ping
from commands.util import prefix
from functions import configuration, spam

parser = ArgumentParser()
parser.add_argument("--debug", help="Set debug logging level")
parser.add_argument("--token", help="Specify your Discord token")
clargs = parser.parse_args()
logging.basicConfig(level=DEBUG if clargs.debug else INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


class Help(Command):
    def __init__(self):
        super().__init__("Shows help")

    async def execute(self, clnt, channel, user, params):
        inf = "**Available commands:**\n------------------------------------\n"
        for key in commands:
            if commands[key].canExecute(user):
                inf += f"{key} : {commands[key].help}\n"
        custom_commands = CustomCommands.getCommands(channel.server)
        if len(custom_commands.keys()):
            inf += "\n**Other commands:**\n------------------------------------\n"
            for key in custom_commands:
                inf += f"{key}\n"

        await clnt.send_message(channel, inf)


dc_client = discord.Client()

commands = {
    "ping": Ping(),
    "stop": Stop(),
    "upgrade": Upgrade(),
    "help": Help(),
    "add": AddCustomCommand(),
    "remove": RemoveCustomCommand()
}


@dc_client.event
async def on_ready():
    global dc_client
    logging.info("Logged in as"
                 f"{dc_client.user.name}"
                 f"{dc_client.user.id}"
                 "------"
                 "Do not create custom commands that might interfere with the commands of other bots"
                 "You can report an Issue/Bug on the GearBot repository (https://github.com/AEnterprise/Gearbot)"
                 "This bot is made by Slak#9006 & AEnterprise#4693"
                 "------")

    for server in dc_client.servers:
        if not configuration.hasconfig(server):
            configuration.createconfigserver(server, True)

    global APP_INFO
    APP_INFO = await dc_client.application_info()
    global DEBUG_MODE
    DEBUG_MODE = (APP_INFO.name == 'SlakBotTest') | (APP_INFO.name == 'Parrot test')


@dc_client.event
async def on_message(message):
    global dc_client
    if (message.content is None) or (message.content == ''):
        return
    elif not (message.content.startswith(prefix) or message.channel.is_private):
        await spam.check_for_spam(dc_client, message)

    if message.content.startswith(prefix):
        cmd, *args = message.content[1:].split()
        logging.debug(f"command '{cmd}' with arguments {args} issued")
    else:
        return

    try:
        if cmd in commands.keys():
            command = commands[cmd]
            if command.canExecute(message.author):
                await command.execute(dc_client, message.channel, message.author, args)
            else:
                await dc_client.send_message(message.channel, "You do not have permission to execute this command")
        else:
            custom_commands = CustomCommands.getCommands(message.channel.server)
            if cmd in custom_commands.keys():
                await dc_client.send_message(message.channel, custom_commands[cmd])
                return
            logging.debug(f"command '{cmd}' not recognized")
    except discord.Forbidden as e:
        logging.info("Bot is not allowed to send messages")
        on_command_error(message.channel, cmd, args, e)
    except discord.InvalidArgument as e:
        on_command_error(message.channel, cmd, args, e)
        logging.info("Exception: Invalid message arguments")
    except Exception as e:
        await on_command_error(message.channel, cmd, args, e)
        traceback.print_exc()


async def on_command_error(channel, cmd, args, exception):
    global dc_client
    try:
        logging.WARNING("Command execution failed:"
                        f"    Command: {cmd}"
                        f"    Arguments: {args}"
                        f"    Channel: {channel.name}"
                        f"    Server: {channel.server}"
                        f"    Exception: {exception}")
        await dc_client.send_message(channel, f"Execution of the {cmd} command failed, please try again later")
    except Exception as e:
        logging.warning(f"Failed to notify caller:\n{e}")


if __name__ == '__main__':
    if 'gearbotlogin' in os.environ:
        token = os.environ['gearbotlogin']
    elif clargs.token:
        token = clargs.token
    else:
        token = input("Please enter your Discord token: ")
    CustomCommands.loadCommands()
    dc_client.run(token)
