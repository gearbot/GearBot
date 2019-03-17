import discord
from discord.ext import commands

from Cogs.BaseCog import BaseCog
from Util import ReactionManager


class ReactionHandler(BaseCog):

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await ReactionManager.on_reaction(self.bot, payload.message_id, payload.channel_id, payload.user_id, str(payload.emoji))

def setup(bot):
    bot.add_cog(ReactionHandler(bot))