import discord
from discord.ext import commands



class AntiRaid:
    def __init__(self, bot):
        self.bot: commands.Bot = bot

    async def sound_the_alarm(self, guild):
        print("alarm triggered!")
        pass

    async def on_member_join(self, member: discord.Member):
        # someone joined, track in redis, query
        pass




def setup(bot):
    bot.add_cog(AntiRaid(bot))
