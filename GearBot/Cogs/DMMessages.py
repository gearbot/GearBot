import discord

from Util import Configuration


class DMMessages:

    def __init__(self, bot):
        self.bot = bot


    async def on_message(self, message: discord.Message):
        if message.guild is not None or len(message.content) > 1800 or message.author.id == self.bot.user.id:
            return
        if not message.content.startswith("!"):
            channel = self.bot.get_channel(Configuration.get_master_var("inbox", 0))
            if channel is not None:
                await channel.send(f"[`{message.created_at.strftime('%c')}`] {message.author} (`{message.author.id}`) said: {message.clean_content}")
            for attachement in message.attachments:
                await channel.send(attachement.url)


def setup(bot):
    bot.add_cog(DMMessages(bot))