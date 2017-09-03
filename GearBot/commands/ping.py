import asyncio
from .command import Command


class Ping(Command):

    def __init__(self):
        super().__init__("Basic ping")

    async def execute(self, client, channel, user, params):
        await (client.send_message(channel, "Pong"))