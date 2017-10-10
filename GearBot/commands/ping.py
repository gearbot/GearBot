from commands.command import Command


class Ping(Command):
    """Basic ping"""

    async def execute(self, client, channel, user, params):
        await (client.send_message(channel, "Pong"))