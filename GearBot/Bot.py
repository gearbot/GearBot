import datetime
import json
import logging
import os
import time
import traceback
from argparse import ArgumentParser
from collections import deque
from logging import DEBUG, INFO

import discord

import Variables
from Util import configuration, spam, GearbotLogging
from Util.Commands import COMMANDS
from commands import CustomCommands
from versions import VersionChecker

dc_client: discord.Client = discord.Client()
MESSAGE_CACHE = dict()


@dc_client.event
async def on_ready():
    if not Variables.HAS_STARTED:

        global dc_client
        Variables.DISCORD_CLIENT = dc_client
        configuration.onReady()
        await GearbotLogging.logToLogChannel(
            f"<:woodGear:344163118089240596> Gearbot startup sequence initialized, spinning up the gears <:woodGear:344163118089240596>")
        Variables.APP_INFO = await dc_client.application_info()

        await CustomCommands.loadCommands()
        await GearbotLogging.logToLogChannel(f"Loaded {Variables.CUSTOM_COMMANDS.__len__()} custom commands")

        VersionChecker.init(dc_client)

        logging.info("Readying commands")
        for command in COMMANDS.values():
            await command.onReady(dc_client)

        logging.info("Populating recent message cache")
        server = discord.utils.get(dc_client.servers, id=configuration.getConfigVar("MAIN_SERVER_ID"))
        gearbot = server.get_member(Variables.APP_INFO.id)
        for channel in server.channels:
            if channel.permissions_for(gearbot).read_messages:
                MESSAGE_CACHE[channel.id] = deque(maxlen=500)
                async for log in dc_client.logs_from(channel, limit=500):
                    if not log.author.bot or log.content is None or log.content == '':
                        MESSAGE_CACHE[channel.id].append({
                            "id": log.id,
                            "content": log.content,
                            "author": log.author,
                            "channelname": log.channel.name
                        })

        if (Variables.DEBUG_MODE):
            await GearbotLogging.logToLogChannel("Gearbot: Testing Editon is now online")
        else:
            await GearbotLogging.logToLogChannel(
                "<:diamondGear:344163228101640192> Gearbot is now online <:diamondGear:344163228101640192>")

        Variables.HAS_STARTED = True
    await dc_client.change_presence(game=discord.Game(name='with gears'))


@dc_client.event
async def on_channel_create(channel: discord.Channel):
    MESSAGE_CACHE[channel.id] = deque(maxlen=500)


@dc_client.event
async def on_member_join(member: discord.Member):
    if member.server.id == configuration.getConfigVar("MAIN_SERVER_ID"):
        await GearbotLogging.logToJoinChannel(
            f":inbox_tray: {member.name}#{member.discriminator} (`{member.id}`) has joined, account created at {member.created_at}")
        if member.id in Variables.MUTED_USERS and time.time() < Variables.MUTED_USERS[member.id]:
            role = discord.utils.get(member.server.roles, id=configuration.getConfigVar("MUTE_ROLE_ID"))
            await dc_client.add_roles(member, role)
            await GearbotLogging.logToModChannel(
                f":zipper_mouth: {member.name}#{member.discriminator} has rejoined the server before his mute time was up and has been re-muted")
            await dc_client.send_message(member,
                                         f"<:ironGear:344163170664841216> You rejoined the server before your mute was over so the role has been re-applied and moderators have been notified, nice try and enjoy the rest of your mute! <:ironGear:344163170664841216>")


@dc_client.event
async def on_member_remove(member):
    if member.server.id == configuration.getConfigVar("MAIN_SERVER_ID"):
            await GearbotLogging.logToJoinChannel(f":outbox_tray: {member.name}#{member.discriminator} (`{member.id}`) has left the server")


@dc_client.event
async def on_socket_raw_receive(thing):
    if isinstance(thing, str):
        info = json.loads(thing)
        if 't' in info.keys() and info['t'] == "MESSAGE_UPDATE" and "author" in info['d'].keys() and not (
                "bot" in info['d']["author"].keys() and info['d']["author"]["bot"]):
            old = None
            after = None
            for message in MESSAGE_CACHE[info['d']["channel_id"]]:
                if message["id"] == info['d']["id"] and message["content"] != info['d']['content']:
                    old = message
                    after = await dc_client.get_message(dc_client.get_channel(info['d']["channel_id"]), info['d']["id"])
                    embed = discord.Embed(timestamp=datetime.datetime.utcfromtimestamp(time.time()))
                    embed.set_author(name=after.author.name, icon_url=after.author.avatar_url)
                    embed.add_field(name="Before", value=message["content"], inline=False)
                    embed.add_field(name="After", value=info['d']['content'], inline=False)
                    await GearbotLogging.logToMinorChannel(
                        f":pencil: Message by {after.author.name}#{after.author.discriminator} in <#{info['d']['channel_id']}> has been edited:",
                        embed=embed)
                    break
            if not old is None:
                MESSAGE_CACHE[info['d']["channel_id"]].remove(old)
                MESSAGE_CACHE[info['d']["channel_id"]].append({
                    "id": after.id,
                    "content": after.content,
                    "author": after.author,
                    "channelname": after.channel.name
                })
        if 't' in info.keys() and info['t'] == "MESSAGE_DELETE":
            for message in MESSAGE_CACHE[info['d']["channel_id"]]:
                if message["id"] == info['d']["id"]:
                    embed = discord.Embed(timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                          description=message["content"])
                    embed.set_author(name=message["author"].name, icon_url=message["author"].avatar_url)
                    embed.set_footer(text=f"Send in #{message['channelname']}")
                    await GearbotLogging.logToMinorChannel(
                        f":wastebasket: Message by {message['author'].name}#{message['author'].discriminator} has been removed in <#{info['d']['channel_id']}>:",
                        embed=embed)
                    break


@dc_client.event
async def on_message(message: discord.Message):
    global dc_client
    client: discord.Client = dc_client
    if (message.content is None) or (message.content == '') or message.author.bot:
        return
    elif not (message.content.startswith(Variables.PREFIX) or message.channel.is_private):
        await spam.check_for_spam(dc_client, message)
    if message.channel.id in MESSAGE_CACHE.keys():
        MESSAGE_CACHE[message.channel.id].append({
            "id": message.id,
            "content": message.content,
            "author": message.author,
            "channelname": message.channel.name
        })
    if message.content.startswith(Variables.PREFIX):
        cmd, *args = message.content[1:].split()
        cmd = cmd.lower()
        logging.debug(f"command '{cmd}' with arguments {args} issued")

        try:
            if message.channel.is_private:
                author = discord.utils.get(dc_client.servers,
                                           id=configuration.getConfigVar("MAIN_SERVER_ID")).get_member(
                    message.author.id)
            else:
                author = message.author
            if cmd in COMMANDS.keys():
                command = COMMANDS[cmd]
                if command.canExecute(author):
                    await command.execute(dc_client, message.channel, author, args)
                    if (command.shouldDeleteTrigger):
                        await dc_client.delete_message(message)
                else:
                    await dc_client.send_message(message.channel,
                                                 ":lock: You do not have permission to execute this command :lock: ")
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
