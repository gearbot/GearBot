import discord

from Util import Configuration


class DMMessages:

    def __init__(self, bot):
        self.bot = bot


    async def on_message(self, message: discord.Message):
        if message.guild is None or len(message.content) > 1800:
            return
        if not message.content.startswith("!"):
            channel = self.bot.get_channel(Configuration.getMasterConfigVar("inbox", 0))
            if channel is not None:
                await channel.send(f"[`{message.created_at.strftime('%c')}`] {message.author} (`{message.author.id}`) said: {message.clean_content}")


def setup(bot):
    bot.add_cog(DMMessages(bot))