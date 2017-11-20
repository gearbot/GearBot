import discord

from commands.command import Command


class Quote(Command):
    """Basic quote"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "Quotes the requested message"
        self.shouldDeleteTrigger = True

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if (len(params) != 1):
            await client.send_message(channel, "Invalid param")
            return

        for ch in channel.server.channels:
            try:
                message:discord.Message = await client.get_message(ch, params[0])
                embed = discord.Embed(colour=discord.Colour(0xd5fff), description=message.content,
                                      timestamp=message.timestamp)
                embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
                embed.set_footer(text=f"Quote requested by {user.name}")
                await client.send_message(channel, embed=embed)
                return

            except Exception as e:
                pass

        await client.send_message(channel, "Unable to find that message")