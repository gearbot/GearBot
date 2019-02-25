import discord

from Cogs.BaseCog import BaseCog
from Util import Features, Configuration


class AntiRaid(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.checking = set()
        self.under_raid = dict()

    async def sound_the_alarm(self, guild, raiders):
        print("alarm triggered!")

    async def on_member_join(self, member: discord.Member):
        if not Features.is_enabled(member.guild.id, "RAID_DETECTION"):
            return
        pipe = self.bot.redis_raid_pool.pipeline()
        guid = member.guild.id
        key = f"raid_tracking:join:{guid}_{member.id}"
        pipe.set(key, member.id)
        pipe.expire(key, Configuration.get_var(member.guild.id, "RAID_TIME_LIMIT"))
        await pipe.execute()
        if guid not in self.checking:
            self.checking.add(guid)
            raiders = set()
            async for key in self.bot.redis_raid_pool.iscan(match=f'raid_tracking:join:{guid}_*'):
                raiders.add(int(key.split("_")[2]))
            if len(raiders) >= Configuration.get_var(guid, "RAID_TRIGGER_AMOUNT"):
                await self.sound_the_alarm(member.guild, raiders)
            self.checking.remove(guid)





def setup(bot):
    bot.add_cog(AntiRaid(bot))
