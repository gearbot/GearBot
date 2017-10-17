import discord
from commands.command import Command 
import Variables
import json


usertomute = '105076359188979712'

# Loads the config

mutedID = Variables.CONFIG_SETTINGS.get('MUTE_ROLE_ID')
modID = Variables.CONFIG_SETTINGS.get('MODERATOR_ID')


class Mute(Command):
    """Applies a role to mute someone by a moderator"""


    def __init__(self, role=modID):
        super().__init__()
        self.extraHelp["info"] = "Mutes a user"

    async def execute(self, client, channel, user, params):
        await (client.send_message(channel, "muted"))
        await client.add_roles(usertomute, mutedID)
