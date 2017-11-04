import discord

from Util import configuration
from commands.command import Command


class Tester(Command):
    """Allows a user to join/leave the testers group"""


    def __init__(self):
        super().__init__()
        self.extraHelp["info"] = "If you are not a tester then you will be granted the tester role, if he is one the role will be removed"
        self.extraHelp["Tester info"] = "Users can join the testers group to help test BuildCraft. From time to time we might want some help in making sure things work as intended. This role will then be pinged and asked to test things (with optionally a test build to use). This testing can be just a single feature or just stability testing in general before a new release"
        self.extraHelp["Obligations"] = "**None**.\nBeing a tester does not require you to be at the ready and test everything whenever you are pinged. All testing is optional but we do ask that if you join the testers group you try to test things from time to time"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        role = discord.utils.get(channel.server.roles, id=configuration.getConfigVar("TESTER_ROLE_ID"))
        member = (channel.server.get_member(user.id))
        if isTester(user):
            await client.remove_roles(member, role)
            await client.send_message(channel, "You are now no longer a tester")
        else:
            await client.add_roles(member, role)
            embed = discord.Embed(title="General tester info")
            embed.add_field(name="What are testers?", value="Testers are people who help test BuildCraft. From time to time we might want some help in making sure things work as intended. Testers will then be pinged and asked to test things (with optionally a test build to use). This testing can be just a single feature or just stability testing in general before a new release")
            embed.add_field(name="Obligations", value="**None**.\nBeing a tester does not require you to be at the ready and test everything whenever you are pinged. All testing is optional but we do ask that if you join the testers group you try to test things from time to time")
            await client.send_message(user, embed=embed)
            await client.send_message(channel, f"Welcome to the testers group {user.name}, please check your DMs for more info")



def isTester(user: discord.user.User)-> bool:
    testerRole = configuration.getConfigVar("TESTER_ROLE_ID")
    if user.roles is None:
        return False
    for role in user.roles:
        if role.id == testerRole:
            return True
    return False