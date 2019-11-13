import discord
from discord.ext import commands

from Cogs.BaseCog import Gear
from Util import ReactionManager


class ReactionHandler(Gear):

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await ReactionManager.on_reaction(self.bot, payload.message_id, payload.channel_id, payload.user_id, payload.emoji)


    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        pipe = self.bot.redis_pool.pipeline()
        pipe.unlink(f"joins:{guild.id}")
        pipe.unlink(f"inf_track:{guild.id}")
        await pipe.execute()

def setup(bot):
    bot.add_cog(ReactionHandler(bot))