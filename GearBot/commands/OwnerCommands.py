import Variables
from commands.command import Command


class OwnerCommand(Command):
    def canExecute(self, user):
        return (user.id == "106354106196570112") or (Variables.DEBUG_MODE and (user.id == "140130139605434369"))


class Stop(OwnerCommand):
    """Stops the bot"""

    async def execute(self, client, channel, user, params):
        await client.send_message(channel, 'Shutting down')
        await client.close()


class Upgrade(OwnerCommand):
    """Perform an upgrade to the latest version"""

    async def execute(self, client, channel, user, params):
        await client.send_message(channel, "I'll be right back with new gears!")
        file = open("upgradeRequest", "w")
        file.write("upgrade requested")
        file.close()
        await client.logout()
        await client.close()
