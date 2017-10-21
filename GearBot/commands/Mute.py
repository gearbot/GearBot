import discord

from commands.RoleCommands import RoleCommand
from Util import configuration



class Mute(RoleCommand):
    """Applies a role to mute someone by a moderator"""


    def __init__(self):
        super().__init__()
        self.extraHelp["info"] = "Mutes a user"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        await client.add_roles(channel.server.get_member(user.id), self.mutedRoles[channel.server.id])
        await client.send_message(channel, "muted") #do not send message until after we (tried) to apply the mute

    def onReady(self, client: discord.Client):
        self.mutedRoles = dict()
        mutedName = configuration.getConfigVar('MUTE_ROLE_NAME')
        for server in client.servers:
            self.mutedRoles[server.id] = discord.utils.get(server.roles, name=mutedName)



