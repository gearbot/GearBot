import logging
import os
import traceback
from argparse import ArgumentParser
from logging import DEBUG, INFO

import discord

from Util import configuration, spam
from Util.Commands import COMMANDS
from Variables import prefix
from commands import CustomCommands
from versions.VersionInfo import initVersionInfo

parser = ArgumentParser()
parser.add_argument("--debug", help="Set debug logging level")
parser.add_argument("--token", help="Specify your Discord token")
clargs = parser.parse_args()
logging.basicConfig(level=DEBUG if clargs.debug else INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


dc_client = discord.Client()




@dc_client.event
async def on_ready():
    global dc_client

    for server in dc_client.servers:
        if not configuration.hasconfig(server):
            configuration.createconfigserver(server, True)

    global APP_INFO
    APP_INFO = await dc_client.application_info()
    global DEBUG_MODE
    DEBUG_MODE = (APP_INFO.name == 'SlakBotTest') | (APP_INFO.name == 'Parrot test')

    await dc_client.change_presence(game=discord.Game(name='gears'))

    initVersionInfo()

    logging.info(DEBUG_MODE)


@dc_client.event
async def on_message(message):
    global dc_client
    if (message.content is None) or (message.content == ''):
        return
    elif not (message.content.startswith(prefix) or message.channel.is_private):
        await spam.check_for_spam(dc_client, message)

    if message.content.startswith(prefix):
        cmd, *args = message.content[1:].split()
        cmd = cmd.lower()
        logging.debug(f"command '{cmd}' with arguments {args} issued")
    else:
        return

    try:
        if cmd in COMMANDS.keys():
            command = COMMANDS[cmd]
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
