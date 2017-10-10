import logging
import os
import traceback
from argparse import ArgumentParser
from logging import DEBUG, INFO


import discord

from Util import configuration, spam, GearbotLogging
from Util.Commands import COMMANDS
from commands import CustomCommands

import Variables

parser = ArgumentParser()
parser.add_argument("--debug", help="Runs the bot in debug mode", dest='debug', action='store_true')
parser.add_argument("--debugLogging", help="Set debug logging level", action='store_true')
parser.add_argument("--token", help="Specify your Discord token")
clargs = parser.parse_args()
Variables.DEBUG_MODE = clargs.debug
logging.basicConfig(level=DEBUG if clargs.debugLogging else INFO,
                    format="%(asctime)s %(levelname)s %(message)s")


dc_client = discord.Client()




@dc_client.event
async def on_ready():
    global dc_client
    Variables.DISCORD_CLIENT = dc_client

    Variables.APP_INFO = await dc_client.application_info()

    await dc_client.change_presence(game=discord.Game(name='gears'))

    configuration.loadconfig()

    await GearbotLogging.logToLogChannel("Gearbot is now online")

@dc_client.event
async def on_message(message):
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
            if cmd in Variables.CUSTOM_COMMANDS.keys():
                await dc_client.send_message(message.channel, Variables.CUSTOM_COMMANDS[cmd])
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



if __name__ == '__main__':
    if 'gearbotlogin' in os.environ:
        token = os.environ['gearbotlogin']
    elif clargs.token:
        token = clargs.token
    else:
        token = input("Please enter your Discord token: ")
    CustomCommands.loadCommands()
    dc_client.run(token)
