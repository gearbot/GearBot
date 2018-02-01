import asyncio
import json
import logging
import time

import discord

import Variables
from Util import configuration, GearbotLogging
from commands.RoleCommands import RoleCommand


class Mute(RoleCommand):
    """Applies a role to mute someone by a moderator"""


    def __init__(self):
        super().__init__()
        self.extraHelp["info"] = "Mutes a user"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if not (len(params) == 2 or len(params) == 3):
            await client.send_message(channel, "I need a target and duration to get the gears turning")
            return None
        if len(params) == 2:
            params.append(params[1][-1:])
            params[1] = params[1][:-1]
        if params[0].startswith("<@"):
            params[0] = params[0][2:][:-1]
        target = channel.server.get_member(params[0])
        if target is None:
            await client.send_message(channel, f"Target not found ({params[0]}")
            return None
        duration = 0
        try:
            duration = int(params[1])
        except Exception as ex:
            await client.send_message(channel, f"{params[1]} is not a valid duration")
            return None
        length = params[2].lower()
        if length == 'h' or length == 'hours':
            duration = duration * 60
            length = 'm'
        if length == 'm' or length == 'minutes':
            duration = duration * 60
            length = 's'
        if not length == 's':
            await client.send_message(channel, f"{length} is not a valid time indicator, please use, h,m or s")
            return None
        Variables.MUTED_USERS[target.id] = time.time() + duration
        await client.add_roles(channel.server.get_member(target.id), discord.utils.get(channel.server.roles, id=configuration.getConfigVar("MUTE_ROLE_ID")))
        saveMutes()
        await client.send_message(channel, f"<@{params[0]}> has been muted")
        await GearbotLogging.logToModChannel(text=f":zipper_mouth: {target.name}#{target.discriminator} (`{target.id}`) has been muted for {params[1]}{params[2]} by {user.name}")

    async def onReady(self, client: discord.Client):
        logging.info("Loading muted users list")
        loadmutes()
        logging.info("Making sure mute role is setup correctly")
        server = discord.utils.get(client.servers, id=configuration.getConfigVar("MAIN_SERVER_ID"))
        role = discord.utils.get(server.roles, id=configuration.getConfigVar("MUTE_ROLE_ID"))
        override = discord.PermissionOverwrite()
        override.send_messages = False
        override.add_reactions = False
        for channel in server.channels:
            await client.edit_channel_permissions(channel, role, override)
        client.loop.create_task(unmuteChecker(client))


def loadmutes():
    try:
        with open('mutes.json', 'r') as jsonfile:
            Variables.MUTED_USERS = json.load(jsonfile)
    except FileNotFoundError:
        logging.error("Unable to load muted users, assuming nobody has been naughty before")
    except Exception as e:
        logging.error("Failed to parse muted users list")
        print(e)
        raise e

def saveMutes():
    with open('mutes.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(Variables.MUTED_USERS, indent=4, skipkeys=True, sort_keys=True)))

async def unmuteChecker(client:discord.Client):
    while not client.is_closed:
        now  = time.time()
        server = discord.utils.get(client.servers, id=configuration.getConfigVar("MAIN_SERVER_ID"))
        role = discord.utils.get(server.roles, id=configuration.getConfigVar("MUTE_ROLE_ID"))
        unmuted = []
        for user, until in Variables.MUTED_USERS.items():
            if until < now:
                u = server.get_member(user)
                await client.remove_roles(u, role)
                await GearbotLogging.logToModChannel(text=f"{u.name}#{u.discriminator} has been unmuted")
                unmuted.append(user)
        for user in unmuted:
            del Variables.MUTED_USERS[user]
        if len(unmuted) > 0:
            saveMutes()
        await asyncio.sleep(5)

