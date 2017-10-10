import Variables
from commands.OwnerCommands import OwnerCommand
from commands.command import Command


class Test(OwnerCommand):
    """Testing things"""

    async def execute(self, client, channel, user, params):
        raise Exception("just making sure this works")
