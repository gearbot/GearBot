
class Command:
    """Base command class"""

    def __init__(self, help):
        self.help = help

    def canExecute(self, user):
        return True

    async def execute(self, client, channel, user, params):
        await client.send_message(channel, "This command doesn't seem to be implemented")
