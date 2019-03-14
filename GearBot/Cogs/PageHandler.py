import discord
from discord.ext import commands

from Cogs.BaseCog import BaseCog
from Util import Pages, Emoji


class PageHandler(BaseCog):

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.message_id) not in Pages.known_messages.keys():
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        user = guild.get_member(payload.user_id)
        if guild.me.id == payload.user_id:
            return
        try:
            message = await self.bot.get_channel(payload.channel_id).get_message(payload.message_id)
        except discord.NotFound:
            pass
        else:
            if str(payload.emoji) == str(Emoji.get_emoji('LEFT')):
                await Pages.update(self.bot, message , "PREV", payload.user_id)
                try:
                    await message.remove_reaction(Emoji.get_emoji('LEFT'), user)
                except discord.Forbidden:
                    pass
            elif str(payload.emoji) == str(Emoji.get_emoji('RIGHT')):
                await Pages.update(self.bot, message, "NEXT", payload.user_id)
                try:
                    await message.remove_reaction(Emoji.get_emoji('RIGHT'), user)
                except discord.Forbidden:
                    pass
def setup(bot):
    bot.add_cog(PageHandler(bot))