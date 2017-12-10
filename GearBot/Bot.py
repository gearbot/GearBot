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
from versions import VersionInfo

dc_client:discord.Client = discord.Client()

@dc_client.event
async def on_ready():
    if not Variables.HAS_STARTED:
        global dc_client
        Variables.DISCORD_CLIENT = dc_client
        configuration.onReady()
        Variables.APP_INFO = await dc_client.application_info()

        await CustomCommands.loadCommands()
        await GearbotLogging.logToLogChannel(f"Loaded {Variables.CUSTOM_COMMANDS.__len__()} custom commands")

        VersionInfo.initVersionInfo()

        await GearbotLogging.logToLogChannel("Readying commands")
        for command in COMMANDS.values():
            command.onReady(dc_client)

        if (Variables.DEBUG_MODE):
            await GearbotLogging.logToLogChannel("Gearbot: Testing Editon is now online")
        else:
            await GearbotLogging.logToLogChannel("Gearbot is now online")


        Variables.HAS_STARTED = True
        # Timer.start_timer(dc_client)
    await dc_client.change_presence(game=discord.Game(name='with gears'))

@dc_client.event
async def on_message(message:discord.Message):
    global dc_client
    client:discord.Client = dc_client
    if (message.content is None) or (message.content == '') or message.author.bot:
        return
    elif not (message.content.startswith(Variables.PREFIX) or message.channel.is_private):
        await spam.check_for_spam(dc_client, message)

    if message.content.startswith(Variables.PREFIX):
        cmd, *args = message.content[1:].split()
        cmd = cmd.lower()
        logging.debug(f"command '{cmd}' with arguments {args} issued")
    elif message.author.id == Variables.AWAITING_REPLY_FROM:
        if message.content.lower() == "yes":
            print("setting new primary release")
            await client.send_typing(Variables.GENERAL_CHANNEL)
            await client.edit_channel(Variables.GENERAL_CHANNEL, topic=f"General discussions about Buildcraft. \nLatest version:{Variables.NEW_PRIMARY_VERSION['BC_VERSION']} \nFull changelog and download: {Variables.NEW_PRIMARY_VERSION['BLOG_LINK']}")
            await client.send_message(message.channel, f"{Variables.NEW_PRIMARY_VERSION['BC_VERSION']} is now the primary release")
            Variables.AWAITING_REPLY_FROM = None
        elif message.content.lower() == "no":
            print("not setting new primary release")
            Variables.AWAITING_REPLY_FROM = None
        else:
            await dc_client.send_message(message.channel, "Sorry but i don't understand what you mean with that, a simple yes/no would be perfect")
        return
    else:
        return

    try:
        if message.channel.is_private:
            author = discord.utils.get(dc_client.servers, id=configuration.getConfigVar("MAIN_SERVER_ID")).get_member(message.author.id)
        else:
            author = message.author
        if cmd in COMMANDS.keys():
            command = COMMANDS[cmd]
            if command.canExecute(author):
                await command.execute(dc_client, message.channel, author, args)
                if (command.shouldDeleteTrigger):
                    await dc_client.delete_message(message)
            else:
                await dc_client.send_message(message.channel, "You do not have permission to execute this command")
        else:
            if cmd in Variables.CUSTOM_COMMANDS.keys():
                await dc_client.send_message(message.channel, Variables.CUSTOM_COMMANDS[cmd])
                return
            logging.debug(f"command '{cmd}' not recognized")
    except discord.Forbidden as e:
        logging.info("Bot is not allowed to send messages")
        await GearbotLogging.on_command_error(message.channel, message.author, cmd, args, e)
    except discord.InvalidArgument as e:
        await GearbotLogging.on_command_error(message.channel, message.author, cmd, args, e)
        logging.info("Exception: Invalid message arguments")
    except Exception as e:
        await GearbotLogging.on_command_error(message.channel, message.author, cmd, args, e)
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
    configuration.loadconfig()
    if 'gearbotlogin' in os.environ:
        token = os.environ['gearbotlogin']
    elif clargs.token:
        token = clargs.token
    elif not configuration.getConfigVar("LOGIN_TOKEN", "0") is "0":
        token = configuration.getConfigVar("LOGIN_TOKEN")
    else:
        token = input("Please enter your Discord token: ")
    dc_client.run(token)
