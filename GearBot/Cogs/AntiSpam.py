from Cogs.BaseCog import BaseCog
from discord.ext import commands
from discord import Object
from discord.guild import Guild
from discord.message import Message
from discord.member import Member
from discord.channel import TextChannel
from Util.SpamBucket import SpamBucket
from Util import Configuration, InfractionUtils, GearbotLogging, Utils
from database.DatabaseConnector import Infraction
import re
import time
import datetime

BUCKET_RE = r"(\d{17,18})-(\d{17,18})-\d+"


class ViolationException(Exception):

    def __init__(self, check, guild: Guild, friendly, member: Member, channel: TextChannel, offending_messages: set):
        self.check = check
        self.guild = guild
        self.friendly = friendly
        self.member = member
        self.channel = channel
        self.offending_messages = offending_messages


class AntiSpam(BaseCog):

    def __init__(self, bot):
        super(AntiSpam, self).__init__(bot)

    def get_bucket(self, guild_id, rule_name):
        cfg = Configuration.get_var(guild_id, "ANTI_SPAM")
        bucket_cfg = cfg.get(rule_name.upper())
        if bucket_cfg is None:
            return None
        c = bucket_cfg.get("COUNT")
        p = bucket_cfg.get("PERIOD")
        return SpamBucket(self.bot.redis_pool, "{}:{}:{}".format(guild_id, rule_name, "{}"), c, p)

    @commands.Cog.listener()
    async def on_message(self, ctx: Message):
        if ctx.author.id == self.bot.user.id:
            return  # Don't track anti-spam for ourselves
        cfg = Configuration.get_var(ctx.guild.id, "ANTI_SPAM")
        if not cfg.get("ENABLED", False):
            return
        try:
            await self.process_message(ctx)
        except ViolationException as ex:
            await self.violate(ex)

    async def process_message(self, ctx: Message):
        # Use the discord's message timestamp to hopefully not trigger false positives
        msg_time = int(ctx.created_at.timestamp()) * 1000

        if self.is_exempt(ctx.guild.id, ctx.author):
            return

        async def check_bucket(check, friendly_text, amount):
            if amount == 0:
                return
            bucket = self.get_bucket(ctx.guild.id, check)
            if bucket is not None and await bucket.check(ctx.author.id, msg_time, amount, f"{ctx.channel.id}-{ctx.id}"):
                count = await bucket.count(ctx.author.id, msg_time, expire=False)
                period = await bucket.size(ctx.author.id, msg_time, expire=False) / 1000
                raise ViolationException(check, ctx.guild, f"{friendly_text} ({count}/{period}s)", ctx.author,
                                         ctx.channel, await bucket.get(ctx.author.id, msg_time, expire=False))

        await check_bucket("max_messages", "Too many messages", 1)
        await check_bucket("max_newlines", "Too many newlines", len(re.split("\\r\\n|\\r|\\n", ctx.content)))
        await check_bucket("max_mentions", "Too many mentions", len(re.findall("<@[!&]?\\d+>", ctx.content)))
        await self.check_duplicates(ctx)

    async def check_duplicates(self, ctx: Message):
        rule = Configuration.get_var(ctx.guild.id, "ANTI_SPAM")["MAX_DUPLICATES"]
        spam_bucket = SpamBucket(self.bot.redis_pool,
                                 "spam:duplicates:{}:{}:{}".format(ctx.guild.id, ctx.author.id, "{}"), rule["COUNT"],
                                 rule["PERIOD"])
        t = int(ctx.created_at.timestamp()) * 1000
        if await spam_bucket.check(ctx.content, t, 1, f"{ctx.channel.id}-{ctx.id}"):
            count = await spam_bucket.count(ctx.content, t, expire=False)
            raise ViolationException("max_duplicates", ctx.guild,
                                     f"Too many duplicates ({count})",
                                     ctx.author, ctx.channel, await spam_bucket.get(ctx.content, t, expire=False))

    async def violate(self, ex: ViolationException):
        lv_key = f"lv:{ex.guild.id}:{ex.member.id}"
        last = await self.bot.redis_pool.get(lv_key)
        if last is None:
            last = 0
        else:
            last = int(last)
        await self.bot.redis_pool.setex(lv_key, 60, int(time.time()))
        if last + 10 < time.time():
            # Punish and Clean
            cfg = Configuration.get_var(ex.guild.id, "ANTI_SPAM")
            punishment = cfg.get("PUNISHMENT", "none").lower()
            duration = cfg.get("PUNIHSMENT_DURATION", 0)
            until = time.time() + duration

            reason = f"Spam Detected in #{ex.channel.name}: {ex.friendly}"
            # TODO 6/3/2019: Log to modlogs
            GearbotLogging.log_to(ex.guild.id, 'spam_violate', user=Utils.clean_user(ex.member), user_id=ex.member.id,
                                  check=ex.check.upper(), friendly=ex.friendly, channel=ex.channel.mention)
            if punishment == "kick":
                self.bot.data["forced_exits"].add(f"{ex.guild.id}-{ex.member.id}")
                await ex.guild.kick(ex.member, reason=reason)
                i = InfractionUtils.add_infraction(ex.guild.id, ex.member.id, self.bot.user.id, 'Kick', reason,
                                                   active=False)
                GearbotLogging.log_to(ex.guild.id, 'kick_log', user=Utils.clean_user(ex.member), user_id=ex.member.id,
                                      moderator=Utils.clean_user(ex.guild.me), moderator_id=ex.guild.me.id,
                                      reason=reason, inf=i.id)
            if punishment == "warn":
                i = InfractionUtils.add_infraction(ex.guild.id, ex.member.id, self.bot.user.id, 'Warn', reason)
                GearbotLogging.log_to(ex.guild.id, 'warning_added_modlog', user=Utils.clean_user(ex.member),
                                      moderator=Utils.clean_user(ex.guild.me), reason=reason,
                                      user_id=ex.member.id, moderator_id=ex.guild.me.id, inf=i.id)
            if punishment == "ban":
                self.bot.data["forced_exists"].add(f"{ex.guild.id}-{ex.member.id}")
                await ex.guild.ban(ex.member, reason=reason, delete_message_days=0)
                Infraction.update(active=False).where(
                    (Infraction.user_id == ex.member.id) & (Infraction.type == "Unban") & (
                            Infraction.guild_id == ex.guild.id)).execute()
                i = InfractionUtils.add_infraction(ex.guild.id, ex.member.id, self.bot.user.id, 'Ban', reason)
                GearbotLogging.log_to(ex.guild.id, 'ban_log', user=Utils.clean_user(ex.member), user_id=ex.member.id,
                                      moderator=Utils.clean_user(ex.guild.me), moderator_id=ex.guild.me.id,
                                      reason=reason, inf=i.id)
            if punishment == "mute":
                role = AntiSpam._get_mute_role(ex.guild)
                if role is not None and ex.guild.me.top_role > role:
                    await ex.member.add_roles(role, reason=reason)
                    i = InfractionUtils.add_infraction(ex.guild.id, ex.member.id, self.bot.user.id, 'Mute', reason,
                                                       end=until)
                    GearbotLogging.log_to(ex.guild.id, 'mute_log',
                                          user=Utils.clean_user(ex.member),
                                          user_id=ex.member.id,
                                          moderator=Utils.clean_user(ex.guild.me.author),
                                          moderator_id=ex.guild.me.id,
                                          duration=f'{duration} seconds',
                                          reason=reason, inf=i.id)
            if punishment == "tempban":
                self.bot.data["forced_exists"].add(f"{ex.guild.id}-{ex.member.id}")
                await ex.guild.ban(ex.member, reason=reason, delete_message_days=0)
                i = InfractionUtils.add_infraction(ex.guild.id, ex.member.id, self.bot.user.id, 'Tempban', reason,
                                                   end=until)
                GearbotLogging.log_to(ex.guild.id, 'tempban_log', user=Utils.clean_user(ex.member),
                                      user_id=ex.member.id, moderator=Utils.clean_user(ex.guild.me),
                                      moderator_id=ex.guild.me.id, reason=reason,
                                      until=datetime.datetime.utcfromtimestamp(until), inf=i.id)

            if cfg.get("CLEAN", False):
                to_clean = AntiSpam._process_bucket_entries(ex.offending_messages)
                by_channel = {}
                for (chan, msg) in to_clean:
                    by_channel.setdefault(chan, []).append(msg)

                for (chan, msgs) in by_channel.items():
                    guild_chan = ex.guild.get_channel(int(chan))
                    msgs = [Object(id=x) for x in msgs]
                    if guild_chan is not None:
                        def divide_msgs(l, n=100):
                            for i in range(0, len(l), n):
                                yield l[i:i + n]

                        # Ensure we only delete 100 at a time. Probably not necessary but you never know with people
                        for group in divide_msgs(msgs):
                            await guild_chan.delete_messages(group)

    @staticmethod
    def is_exempt(guild_id, member: Member):
        config = Configuration.get_var(guild_id, "ANTI_SPAM")
        for role in member.roles:
            if str(role.id) in config["EXEMPT_ROLES"]:
                return True
        return member.id in config["EXEMPT_USERS"]

    @staticmethod
    def _get_mute_role(guild):
        role_id = Configuration.get_var(guild.id, "MUTE_ROLE")
        if role_id is 0:
            return None
        role = guild.get_role(role_id)
        return role

    @staticmethod
    def _process_bucket_entries(entries):
        def extract_re(key):
            matches = re.findall(BUCKET_RE, key)
            if len(matches) > 0:
                return matches[0][0], matches[0][1]
            else:
                return None

        return set(filter(lambda x: x is not None, map(extract_re, entries)))


def setup(bot):
    bot.add_cog(AntiSpam(bot))
