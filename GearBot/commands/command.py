
class Command:
    """Base command class"""

    def __init__(self, help, extrahelp = None):
        self.help = help
        self.extraHelp = extrahelp

    def canExecute(self, user):
        return True

    async def execute(self, client, channel, user, params):
        await client.send_message(channel, "This command doesn't seem to be implemented")

    async def sendHelp(self, client, channel):
        message = self.extraHelp
        if message is None:
            message = self.help
        await client.send_message(channel, message)