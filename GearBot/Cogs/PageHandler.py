import discord
from discord.ext import commands

from Util import Pages


class PageHandler:
    def __init__(self, bot):
        self.bot:commands.Bot = bot

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        user = guild.get_member(payload.user_id)
        if guild.me.id == payload.user_id:
            return
        message = await self.bot.get_channel(payload.channel_id).get_message(payload.message_id)
        if payload.emoji.id == Pages.prev_id:
            if await Pages.update(self.bot, message , "PREV", payload.user_id):
                await message.remove_reaction(Pages.prev_emoji, user)
        elif payload.emoji.id == Pages.next_id:
            if await Pages.update(self.bot, message, "NEXT", payload.user_id):
                await message.remove_reaction(Pages.next_emoji, user)

def setup(bot):
    bot.add_cog(PageHandler(bot))