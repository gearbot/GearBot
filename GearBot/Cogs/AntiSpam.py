from Cogs.BaseCog import BaseCog
from discord.ext import commands
from discord.message import Message
from discord.member import Member
from discord.channel import TextChannel
from Util.SpamBucket import SpamBucket
import re
import time


class ViolationException(Exception):

    def __init__(self, check, guild, friendly, member: Member, channel: TextChannel):
        self.check = check
        self.guild = guild
        self.friendly = friendly
        self.member = member
        self.channel = channel


class AntiSpam(BaseCog):

    def __init__(self, bot):
        super(AntiSpam, self).__init__(bot)
        # TODO 6/1/2019: Put this actually somewhere good
        self.rules = {
            "max_messages": {
                "count": 10,
                "period": 10
            },
            "max_newlines": {
                "count": 20,
                "period": 60
            },
            "max_links": {
                "count": 10,
                "period": 60
            },
            "max_duplicates": {
                "count": 10,
                "period": 30
            }
        }
        self.punishment = "KICK"

    def get_bucket(self, guild_id, rule_name):
        r = self.rules[rule_name]
        c = r.get("count")
        p = r.get("period")
        return SpamBucket(self.bot.redis_pool, "{}:{}:{}".format(guild_id, rule_name, "{}"), c, p)

    @commands.Cog.listener()
    async def on_message(self, ctx: Message):
        if ctx.author.id == self.bot.user.id:
            return  # Don't track anti-spam for ourselves
        try:
            await self.process_message(ctx)
        except ViolationException as ex:
            await self.violate(ex)

    async def process_message(self, ctx: Message):
        async def check_bucket(check, friendly_text, amount):
            print(f"Checking bucket {check}")
            if amount == 0:
                return
            bucket = self.get_bucket(ctx.guild.id, check)
            if await bucket.check(ctx.author.id, amount):
                count = await bucket.count(ctx.author.id)
                period = await bucket.size(ctx.author.id) / 1000
                raise ViolationException(check, ctx.guild, f"{friendly_text} ({count}/{period}s)", ctx.author,
                                         ctx.channel)

        await check_bucket("max_messages", "too many messages", 1)
        await check_bucket("max_newlines", "too many newlines", len(re.split("\\r\\n|\\r|\\n", ctx.content)))
        await check_bucket("max_mentions", "too many mentions", len(re.findall("<@[!&]?\\d+>", ctx.content)))

    def check_duplicates(self, ctx: Message):
        # TODO 6/1/2019: This
        pass

    async def violate(self, ex: ViolationException):
        lv_key = f"lv:{ex.guild.id}:{ex.member.id}"
        last = await self.bot.redis_pool.get(lv_key)
        if last is None:
            last = 0
        else:
            last = int(last)
        await self.bot.redis_pool.setex(lv_key, 60, int(time.time()))
        if last + 10 < time.time():
            print("This is the part where you get " + self.punishment + " " + ex.friendly)


def setup(bot):
    bot.add_cog(AntiSpam(bot))
