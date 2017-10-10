from commands.command import Command


class Ping(Command):
    """Basic ping"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Just pongs"

    async def execute(self, client, channel, user, params):
        await (client.send_message(channel, "Pong"))