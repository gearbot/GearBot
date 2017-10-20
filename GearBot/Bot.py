import logging
import os
import traceback
from argparse import ArgumentParser
from logging import DEBUG, INFO

import discord

import Variables
from Util import configuration, spam, GearbotLogging
from Util.Commands import COMMANDS
from commands import CustomCommands

dc_client = discord.Client()

@dc_client.event
async def on_ready():
    if not Variables.HAS_STARTED:
        global dc_client
        Variables.DISCORD_CLIENT = dc_client
        configuration.onReady()
        Variables.APP_INFO = await dc_client.application_info()

        for server in dc_client.servers:
            logging.info(f"Loading commands for {server.name} ({server.id})")
            CustomCommands.loadCommands(server.id)

        await dc_client.change_presence(game=discord.Game(name='gears'))
        await GearbotLogging.logToLogChannel("Gearbot: Testing Editon is now online")
        Variables.HAS_STARTED = True

@dc_client.event
async def on_message(message:discord.Message):
    global dc_client
    if (message.content is None) or (message.content == ''):
        return
    elif not (message.content.startswith(Variables.PREFIX) or message.channel.is_private):
        await spam.check_for_spam(dc_client, message)

    if message.content.startswith(Variables.PREFIX):
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
            customCommands = CustomCommands.getCommands(message.server.id)
            if cmd in customCommands.keys():
                await dc_client.send_message(message.channel, customCommands[cmd])
                return
            logging.debug(f"command '{cmd}' not recognized")
    except discord.Forbidden as e:
        logging.info("Bot is not allowed to send messages")
        await GearbotLogging.on_command_error(message.channel, cmd, args, e)
    except discord.InvalidArgument as e:
        await GearbotLogging.on_command_error(message.channel, cmd, args, e)
        logging.info("Exception: Invalid message arguments")
    except Exception as e:
        await GearbotLogging.on_command_error(message.channel, cmd, args, e)
        traceback.print_exc()



parser = ArgumentParser()
parser.add_argument("--debug", help="Runs the bot in debug mode", dest='debug', action='store_true')
parser.add_argument("--debugLogging", help="Set debug logging level", action='store_true')
parser.add_argument("--token", help="Specify your Discord token")

clargs = parser.parse_args()
Variables.DEBUG_MODE = clargs.debug
logging.basicConfig(level=DEBUG if clargs.debugLogging else INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


if __name__ == '__main__':
    if 'gearbotlogin' in os.environ:
        token = os.environ['gearbotlogin']
    elif clargs.token:
        token = clargs.token
    elif not configuration.getConfigVar("LOGIN_TOKEN", "0") is "0":
        token = configuration.getConfigVar("LOGIN_TOKEN")
    else:
        token = input("Please enter your Discord token: ")
    dc_client.run(token)
