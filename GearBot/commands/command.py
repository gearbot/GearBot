import discord


class Command:
    """Base command class"""

    def __init__(self) -> None:
        self.extraHelp = dict()
        self.extraHelp["info"] = "I'm sorry but i don't have any more info for this command"

    def canExecute(self, user:discord.user.User)->bool:
        return True

    async def execute(self, client:discord.Client, channel:discord.Channel, user:discord.user.User, params):
        await client.send_message(channel, "This command doesn't seem to be implemented")

    async def sendHelp(self, client, channel):
        embed = discord.Embed(colour=discord.Colour(0x663399))
        embed.description = self.extraHelp["info"]

        embed.set_author(name=self.__class__.__name__ + " command info")

        for key in self.extraHelp.keys():
            if not key == "info":
                embed.add_field(name=key , value=self.extraHelp[key])

        await client.send_message(channel, embed=embed)