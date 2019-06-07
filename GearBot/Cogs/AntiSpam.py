import asyncio
import datetime
import re
import time

from discord import Object, Forbidden, NotFound
from discord.channel import TextChannel
from discord.ext import commands
from discord.guild import Guild
from discord.member import Member
from discord.message import Message

from Cogs.BaseCog import BaseCog
from Util import Configuration, InfractionUtils, GearbotLogging, Utils, Translator, MessageUtils, \
    Permissioncheckers
from Util.SpamBucket import SpamBucket
from database.DatabaseConnector import Infraction

MENTION_RE = re.compile("<@[!&]?\\d+>")


class Violation:

    def __init__(self, check, guild: Guild, friendly, member: Member, channel: TextChannel, offending_messages: set,
                 bucket, count):
        self.check = check
        self.guild = guild
        self.friendly = friendly
        self.member = member
        self.channel = channel
        self.offending_messages = offending_messages
        self.bucket = bucket
        self.count = count


class AntiSpam(BaseCog):

    def __init__(self, bot):
        super(AntiSpam, self).__init__(bot)
        # store values as functions so only what is needed is computed
        self.generators = {
            "max_messages": lambda m: 1,
            "max_newlines": lambda m: len(m.content.split("\n")),
            "max_mentions": lambda m: len(MENTION_RE.findall(m.content))
        }

        self.punishments = {
            "warn": self.warn_punishment,
            "mute": self.mute_punishment,
            "kick": self.kick_punishment,
            "temp_ban": self.temp_ban_punishment,
            "ban": self.ban_punishment
        }

        self.seriousness = {
            "warn": 1,
            "mute": 2,
            "kick": 3,
            "temp_ban": 4,
            "ban": 5
        }
        self.recent = dict()

    def get_bucket(self, guild_id, rule_name, bucket_info, member_id):
        key = f"{guild_id}-{member_id}-{bucket_info['TYPE']}"
        old = self.recent.get(key, 0)
        c = bucket_info.get("SIZE").get("COUNT") +old
        p = bucket_info.get("SIZE").get("PERIOD")
        return SpamBucket(self.bot.redis_pool, "{}:{}:{}".format(guild_id, rule_name, "{}"), c, p)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.id == self.bot.user.id or message.guild is None:
            return  # Don't track anti-spam for ourselves or DMs
        cfg = Configuration.get_var(message.guild.id, "ANTI_SPAM")
        if not cfg.get("ENABLED", False):
            return
        await self.process_message(message)

    async def process_message(self, message: Message):
        # print(f'{datetime.datetime.now().isoformat()} - Processing message')
        if self.is_exempt(message.guild.id, message.author):
            return

        # Use the discord's message timestamp to hopefully not trigger false positives
        msg_time = int(message.created_at.timestamp()) * 1000

        async def check_bucket(check, friendly_text, amount, b):
            # print(f"{check} - {amount}")
            if amount == 0:
                return
            bucket = self.get_bucket(message.guild.id, check, b, message.author.id)
            if bucket is not None and await bucket.check(message.author.id, msg_time, amount,
                                                         f"{message.channel.id}-{message.id}"):
                count = await bucket.count(message.author.id, msg_time, expire=False)
                period = await bucket.size(message.author.id, msg_time, expire=False) / 1000
                self.bot.loop.create_task(self.violate(Violation(check, message.guild, f"{friendly_text} ({count}/{period}s)", message.author,
                                message.channel, await bucket.get(message.author.id, msg_time, expire=False),
                                b, count)))

        counters = dict()
        buckets = Configuration.get_var(message.guild.id, "ANTI_SPAM")["BUCKETS"]

        # so if someone does 20 levels of too many mentions for some stupid reason we don't end up running the same regex 20 times for nothing
        cache = dict()
        for bucket in buckets:
            t = bucket["TYPE"]
            counter = counters.get(t, 0)
            if t == "duplicates":
                await self.check_duplicates(message, counter, bucket)
            else:
                if t in cache:
                    v = cache[t]
                else:
                    v = self.generators[t](message)
                    cache[t] = v
                await check_bucket(f"{t}:{counter}", Translator.translate(f"spam_{t}", message), v, bucket)

    async def check_duplicates(self, message: Message, count: int, bucket):
        rule = bucket["SIZE"]
        key = f"{message.guild.id}-{message.author.id}-{bucket['TYPE']}"
        old = self.recent.get(key, 0)
        spam_bucket = SpamBucket(self.bot.redis_pool,
                                 f"spam:duplicates{count}:{message.guild.id}:{message.author.id}:{'{}'}", rule["COUNT"] + old,
                                 rule["PERIOD"])
        t = int(message.created_at.timestamp()) * 1000
        if await spam_bucket.check(message.content, t, 1, f"{message.channel.id}-{message.id}"):
            count = await spam_bucket.count(message.content, t, expire=False)
            str = Translator.translate('spam_max_duplicates', message)
            self.bot.loop.create_task(self.violate(Violation("max_duplicates", message.guild,
                            f"{str} ({count})",
                            message.author, message.channel,
                            await spam_bucket.get(message.content, t, expire=False), bucket, count)))


    async def violate(self, v: Violation):
        # deterining current punishment
        punish_info = v.bucket["PUNISHMENT"]
        t = punish_info["TYPE"]
        self.bot.dispatch('spam_violation', v)
        key = f"{v.guild.id}-{v.member.id}-{v.bucket['TYPE']}"
        self.recent[key] = self.recent.get(key, 0) + v.count

        # Punish and Clean
        GearbotLogging.log_to(v.guild.id, 'spam_violate', user=Utils.clean_user(v.member), user_id=v.member.id,
                              check=v.check.upper(), friendly=v.friendly, channel=v.channel.mention)

        await self.punishments[t](v)

        if v.bucket.get("CLEAN", True):
            to_clean = AntiSpam._process_bucket_entries(v.offending_messages)
            by_channel = {}
            for (chan, msg) in to_clean:
                by_channel.setdefault(chan, []).append(msg)

            for (chan, msgs) in by_channel.items():
                guild_chan = v.guild.get_channel(int(chan))
                msgs = [Object(id=x) for x in msgs]
                if guild_chan is not None:
                    # Ensure we only delete 100 at a time. Probably not necessary but you never know with people
                    for group in Utils.chunks(msgs, 100):
                        try:
                            await guild_chan.delete_messages(group)
                        except NotFound:
                            pass
        await asyncio.sleep(v.bucket["SIZE"]["PERIOD"] - 0.5)
        old = self.recent.get(key, 0)
        new = old - v.count
        if new <= 0:
            del self.recent[key]
        else:
            self.recent[key] = new


    async def warn_punishment(self, v: Violation):
        reason = self.assemble_reason(v)
        i = InfractionUtils.add_infraction(v.guild.id, v.member.id, self.bot.user.id, 'Warn', reason)
        GearbotLogging.log_to(v.guild.id, 'warning_added_modlog', user=Utils.clean_user(v.member),
                              moderator=Utils.clean_user(v.guild.me), reason=reason,
                              user_id=v.member.id, moderator_id=v.guild.me.id, inf=i.id)
        try:
            dm_channel = await v.member.create_dm()
            await dm_channel.send(MessageUtils.assemble(dm_channel, 'WARNING', 'warning_dm', server=v.member.guild.name) + f"```{reason}```")
        except Forbidden:
            GearbotLogging.log_to(v.member.guild.id, 'warning_could_not_dm',
                                  user=Utils.escape_markdown(v.member.name), userid=v.member.id)

    async def mute_punishment(self, v: Violation):
        duration = v.bucket["PUNISHMENT"]["DURATION"]
        until = time.time() + duration
        reason = self.assemble_reason(v)
        role = AntiSpam._get_mute_role(v.guild)
        if role is not None and v.guild.me.top_role > role:
            await v.member.add_roles(role, reason=reason)
            i = InfractionUtils.add_infraction(v.guild.id, v.member.id, self.bot.user.id, 'Mute', reason,
                                               end=until)
            GearbotLogging.log_to(v.guild.id, 'mute_log',
                                  user=Utils.clean_user(v.member),
                                  user_id=v.member.id,
                                  moderator=Utils.clean_user(v.guild.me),
                                  moderator_id=v.guild.me.id,
                                  duration=f'{duration} seconds',
                                  reason=reason, inf=i.id)

    async def kick_punishment(self, v: Violation):
        reason = self.assemble_reason(v)
        self.bot.data["forced_exits"].add(f"{v.guild.id}-{v.member.id}")
        await v.guild.kick(v.member, reason=reason)
        i = InfractionUtils.add_infraction(v.guild.id, v.member.id, self.bot.user.id, 'Kick', reason,
                                           active=False)
        GearbotLogging.log_to(v.guild.id, 'kick_log', user=Utils.clean_user(v.member), user_id=v.member.id,
                              moderator=Utils.clean_user(v.guild.me), moderator_id=v.guild.me.id,
                              reason=reason, inf=i.id)

    async def temp_ban_punishment(self, v: Violation):
        reason = self.assemble_reason(v)
        duration = v.bucket["PUNISHMENT"]["DURATION"]
        until = time.time() + duration
        self.bot.data["forced_exists"].add(f"{v.guild.id}-{v.member.id}")
        await v.guild.ban(v.member, reason=reason, delete_message_days=0)
        i = InfractionUtils.add_infraction(v.guild.id, v.member.id, self.bot.user.id, 'Tempban', reason,
                                           end=until)
        GearbotLogging.log_to(v.guild.id, 'tempban_log', user=Utils.clean_user(v.member),
                              user_id=v.member.id, moderator=Utils.clean_user(v.guild.me),
                              moderator_id=v.guild.me.id, reason=reason,
                              until=datetime.datetime.utcfromtimestamp(until), inf=i.id)

    async def ban_punishment(self, v: Violation):
        reason = self.assemble_reason(v)
        self.bot.data["forced_exits"].add(f"{v.guild.id}-{v.member.id}")
        await v.guild.ban(v.member, reason=reason, delete_message_days=0)
        Infraction.update(active=False).where(
            (Infraction.user_id == v.member.id) & (Infraction.type == "Unban") & (
                    Infraction.guild_id == v.guild.id)).execute()
        i = InfractionUtils.add_infraction(v.guild.id, v.member.id, self.bot.user.id, 'Ban', reason)
        GearbotLogging.log_to(v.guild.id, 'ban_log', user=Utils.clean_user(v.member), user_id=v.member.id,
                              moderator=Utils.clean_user(v.guild.me), moderator_id=v.guild.me.id,
                              reason=reason, inf=i.id)

    @staticmethod
    def assemble_reason(v):
        return Translator.translate('spam_infraction_reason', v.guild, channel=f"#{v.channel}",
                                    friendly=v.friendly)

    @staticmethod
    def is_exempt(guild_id, member: Member):
        config = Configuration.get_var(guild_id, "ANTI_SPAM")
        for role in member.roles:
            if role.id in config["EXEMPT_ROLES"]:
                return True
        return member.id in config["EXEMPT_USERS"] or Permissioncheckers.is_mod(member)

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
            parts = key.split("-")
            if len(parts) != 3:
                return None
            return parts[0], parts[1]

        return set(filter(lambda x: x is not None, map(extract_re, entries)))


def setup(bot):
    bot.add_cog(AntiSpam(bot))
