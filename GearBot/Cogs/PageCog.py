import discord
from discord.ext import commands

from Util import Pages


class PageCog:
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    async def on_reaction_add(self, reaction:discord.Reaction, user):
        if reaction.message.guild.me.id == user.id:
            return
        if reaction.custom_emoji and reaction.emoji.id == Pages.prev_id:
            if await Pages.update(reaction.message, "PREV"):
                await reaction.message.remove_reaction(Pages.prev_emoji, user)
        elif reaction.custom_emoji and reaction.emoji.id == Pages.next_id:
            if await Pages.update(reaction.message, "NEXT"):
                await reaction.message.remove_reaction(Pages.next_emoji, user)

def setup(bot):
    bot.add_cog(PageCog(bot))