import discord

from Bot.GearBot import GearBot
from Util import Features


class AntiRaid:
    def __init__(self, bot):
        self.bot: GearBot = bot

    async def sound_the_alarm(self, guild):
        print("alarm triggered!")
        pass

    async def on_member_join(self, member: discord.Member):
        if not Features.is_enabled(member.guild.id, "ANTI_RAID"):
            return
        pipe = self.bot.redis_raid_pool.pipeline()
        pipe.set(f"")




def setup(bot):
    bot.add_cog(AntiRaid(bot))
