from commands.command import Command


class Test(Command):

    def __init__(self):
        super().__init__("Testing things")

    async def execute(self, client, channel, user, params):
        raise Exception("how does this work?")