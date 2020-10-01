import asyncio
import datetime
import re

import emoji
from asyncio.base_futures import CancelledError

import time
from collections import deque
from weakref import WeakValueDictionary

from discord import Object, Forbidden, NotFound
from discord.channel import TextChannel
from discord.ext import commands
from discord.guild import Guild
from discord.member import Member
from discord.message import Message

from Bot import TheRealGearBot
from Cogs.BaseCog import BaseCog
from Util import Configuration, InfractionUtils, GearbotLogging, Utils, Translator, MessageUtils, \
    Permissioncheckers
from Util.Matchers import MENTION_MATCHER, URL_MATCHER
from Util.SpamBucket import SpamBucket
from database.DatabaseConnector import Infraction




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


class ActionHolder:

    def __init__(self, count: int):
        self.count = count

EMOJI_REGEX = re.compile('([^<]*)<a?:(?:[^:]+):([0-9]+)>')
class AntiSpam(BaseCog):

    def __init__(self, bot):
        super(AntiSpam, self).__init__(bot)
        # store values as functions so only what is needed is computed
        self.generators = {
            "max_messages": lambda m: 1,
            "max_newlines": lambda m: len(m.content.split("\n")) - 1,
            "max_mentions": lambda m: len(MENTION_MATCHER.findall(m.content)),
            "max_links": lambda m: len(URL_MATCHER.findall(m.content)),
            "max_emoji": lambda m: len([1 for c in m if c not in reversed(emoji.UNICODE_EMOJI)]) + len(EMOJI_REGEX.findall(m))
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
        self.extra_actions = WeakValueDictionary()
        self.processed = deque(maxlen=500)
        self.censor_processed = deque(maxlen=50)
        self.running = True
        bot.loop.create_task(self.censor_detector())

    def cog_unload(self):
        self.running = False

    def get_extra_actions(self, key):
        if key not in self.extra_actions:
            a = ActionHolder(0)
            self.extra_actions[key] = a

        return self.extra_actions[key]

    def get_bucket(self, guild_id, rule_name, bucket_info, member_id):
        key = f"{guild_id}-{member_id}-{bucket_info['TYPE']}"
        c = bucket_info.get("SIZE").get("COUNT")
        p = bucket_info.get("SIZE").get("PERIOD")
        return SpamBucket(self.bot.redis_pool, "{}:{}:{}".format(guild_id, rule_name, "{}"), c, p,
                          self.get_extra_actions(key))

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.id == self.bot.user.id or message.guild is None:
            return  # Don't track anti-spam for ourselves or DMs
        cfg = Configuration.get_var(message.guild.id, "ANTI_SPAM")
        if not cfg.get("ENABLED", False) or message.id in self.processed:
            return
        self.processed.append(message.id)
        await self.process_message(message)

    async def process_message(self, message: Message):
        # print(f'{datetime.datetime.now().isoformat()} - Processing message')
        if message.webhook_id is not None or self.is_exempt(message.guild.id, message.author):
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
                self.bot.loop.create_task(
                    self.violate(Violation(check, message.guild, f"{friendly_text} ({count}/{period}s)", message.author,
                                           message.channel, await bucket.get(message.author.id, msg_time, expire=False),
                                           b, count)))

        counters = dict()
        buckets = Configuration.get_var(message.guild.id, "ANTI_SPAM", "BUCKETS", [])

        # so if someone does 20 levels of too many mentions for some stupid reason we don't end up running the same regex 20 times for nothing
        cache = dict()
        for bucket in buckets:
            t = bucket["TYPE"]
            counter = counters.get(t, 0)
            if t == "duplicates":
                await self.check_duplicates(message, counter, bucket)
            else:
                v = 0
                if t in cache:
                    v = cache[t]
                elif t in self.generators:
                    v = self.generators[t](message)
                    cache[t] = v
                if v is not 0:
                    await check_bucket(f"{t}:{counter}", Translator.translate(f"spam_{t}", message), v, bucket)

    async def check_duplicates(self, message: Message, count: int, bucket):
        rule = bucket["SIZE"]
        key = f"{message.guild.id}-{message.author.id}-{bucket['TYPE']}"
        full_content = message.content + "\n".join(str(a) for a in message.attachments)
        spam_bucket = SpamBucket(self.bot.redis_pool,
                                 f"spam:duplicates{count}:{message.guild.id}:{message.author.id}:{'{}'}", rule["COUNT"],
                                 rule["PERIOD"], self.get_extra_actions(key))
        t = int(message.created_at.timestamp()) * 1000
        if await spam_bucket.check(full_content, t, 1, f"{message.channel.id}-{message.id}"):
            count = await spam_bucket.count(full_content, t, expire=False)
            period = await spam_bucket.size(message.author.id, t, expire=False) / 1000
            st = Translator.translate('spam_max_duplicates', message)
            self.bot.loop.create_task(self.violate(Violation("max_duplicates", message.guild,
                                                             f"{st} ({count}/{period}s)",
                                                             message.author, message.channel,
                                                             await spam_bucket.get(full_content, t, expire=False),
                                                             bucket, count)))

    async def violate(self, v: Violation):
        # deterining current punishment
        punish_info = v.bucket["PUNISHMENT"]
        t = punish_info["TYPE"]
        self.bot.dispatch('spam_violation', v)
        key = f"{v.guild.id}-{v.member.id}-{v.bucket['TYPE']}"
        a = self.get_extra_actions(key)
        a.count += v.count

        # Punish and Clean
        GearbotLogging.log_key(v.guild.id, 'spam_violate', user=Utils.clean_user(v.member), user_id=v.member.id,
                               check=v.check.upper(), friendly=v.friendly, channel=v.channel.mention, punishment_type=t)

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
        await asyncio.sleep(v.bucket["SIZE"]["PERIOD"])
        a = self.get_extra_actions(key)
        a.count -= v.count

    async def warn_punishment(self, v: Violation):
        reason = v.bucket["PUNISHMENT"].get("REASON", self.assemble_reason(v))
        i = await InfractionUtils.add_infraction(v.guild.id, v.member.id, self.bot.user.id, 'Warn', reason)
        GearbotLogging.log_key(v.guild.id, 'warning_added_modlog', user=Utils.clean_user(v.member),
                               moderator=Utils.clean_user(v.guild.me), reason=reason,
                               user_id=v.member.id, moderator_id=v.guild.me.id, inf=i.id)
        try:
            dm_channel = await v.member.create_dm()
            await dm_channel.send(MessageUtils.assemble(dm_channel, 'WARNING', 'warning_dm',
                                                        server=v.member.guild.name) + f"```{reason}```")
        except Forbidden:
            GearbotLogging.log_key(v.member.guild.id, 'warning_could_not_dm',
                                   user=Utils.escape_markdown(v.member.name), userid=v.member.id)

    async def mute_punishment(self, v: Violation):
        duration = v.bucket["PUNISHMENT"]["DURATION"]
        until = time.time() + duration
        reason = self.assemble_reason(v)
        role = AntiSpam._get_mute_role(v.guild)
        i = await Infraction.get_or_none(user_id = v.member.id, type = "Mute", guild_id = v.member.guild.id, active=True)
        if i is None:
            i = await InfractionUtils.add_infraction(v.guild.id, v.member.id, self.bot.user.id, 'Mute', reason,
                                               end=until)
            try:
                await v.member.add_roles(role, reason=reason)
            except Forbidden:
                GearbotLogging.log_key(v.guild.id, 'mute_punishment_failure',
                                       user=Utils.clean_user(v.member),
                                       user_id=v.member.id,
                                       duration=Utils.to_pretty_time(duration, v.guild.id),
                                       reason=reason, inf=i.id)
            else:
                GearbotLogging.log_key(v.guild.id, 'mute_log',
                                       user=Utils.clean_user(v.member),
                                       user_id=v.member.id,
                                       moderator=Utils.clean_user(v.guild.me),
                                       moderator_id=v.guild.me.id,
                                       duration=Utils.to_pretty_time(duration, v.guild.id),
                                       reason=reason, inf=i.id)
        else:
            i.end += datetime.timedelta(seconds=duration)
            i.reason += f'+ {reason}'
            i.save()
            GearbotLogging.log_key(v.guild.id, 'mute_duration_extended_log',
                                   user=Utils.clean_user(v.member),
                                   user_id=v.member.id,
                                   moderator=Utils.clean_user(v.guild.me),
                                   moderator_id=v.guild.me.id,
                                   duration=Utils.to_pretty_time(duration, v.guild.id),
                                   reason=reason, inf_id=i.id, end=i.end)
            InfractionUtils.clear_cache(v.guild.id)

    async def kick_punishment(self, v: Violation):
        reason = self.assemble_reason(v)
        i = await InfractionUtils.add_infraction(v.guild.id, v.member.id, self.bot.user.id, 'Kick', reason,
                                           active=False)
        self.bot.data["forced_exits"].add(f"{v.guild.id}-{v.member.id}")
        try:
            await v.guild.kick(v.member, reason=reason)
        except Forbidden:
            GearbotLogging.log_key(v.guild.id, 'kick_punishment_failure', user=Utils.clean_user(v.member), user_id=v.member.id,
                                   moderator=Utils.clean_user(v.guild.me), moderator_id=v.guild.me.id,
                                   reason=reason, inf=i.id)
        else:
            GearbotLogging.log_key(v.guild.id, 'kick_log', user=Utils.clean_user(v.member), user_id=v.member.id,
                                   moderator=Utils.clean_user(v.guild.me), moderator_id=v.guild.me.id,
                                   reason=reason, inf=i.id)

    async def temp_ban_punishment(self, v: Violation):
        reason = self.assemble_reason(v)
        duration = v.bucket["PUNISHMENT"]["DURATION"]
        until = time.time() + duration
        self.bot.data["forced_exists"].add(f"{v.guild.id}-{v.member.id}")
        await v.guild.ban(v.member, reason=reason, delete_message_days=0)
        i = await InfractionUtils.add_infraction(v.guild.id, v.member.id, self.bot.user.id, 'Tempban', reason,
                                           end=until)
        GearbotLogging.log_key(v.guild.id, 'tempban_log', user=Utils.clean_user(v.member),
                               user_id=v.member.id, moderator=Utils.clean_user(v.guild.me),
                               moderator_id=v.guild.me.id, reason=reason,
                               until=datetime.datetime.utcfromtimestamp(until), inf=i.id)

    async def ban_punishment(self, v: Violation):
        reason = self.assemble_reason(v)
        self.bot.data["forced_exits"].add(f"{v.guild.id}-{v.member.id}")
        await v.guild.ban(v.member, reason=reason, delete_message_days=0)
        await Infraction.filter(user_id=v.member.id, type="Unban", guild_id=v.guild.id).update(active=False)
        i = await InfractionUtils.add_infraction(v.guild.id, v.member.id, self.bot.user.id, 'Ban', reason)
        GearbotLogging.log_key(v.guild.id, 'ban_log', user=Utils.clean_user(v.member), user_id=v.member.id,
                               moderator=Utils.clean_user(v.guild.me), moderator_id=v.guild.me.id,
                               reason=reason, inf=i.id)


    async def censor_detector(self):
        # reciever taks for someone gets censored
        while self.running:
            try:
                message = None
                message = await self.bot.wait_for("user_censored")
                # make sure our cog is still running so we don't handle it twice
                if not self.running:
                    return

                # make sure anti-spam is enabled
                cfg = Configuration.get_var(message.guild.id, "ANTI_SPAM")
                if not cfg.get("ENABLED", False) or message.id in self.censor_processed:
                    continue
                buckets = Configuration.get_var(message.guild.id, "ANTI_SPAM", "BUCKETS", [])
                count = 0
                for b in buckets:
                    t = b["TYPE"]
                    if t == "censored":
                        msg_time = int(message.created_at.timestamp()) * 1000
                        bucket = self.get_bucket(message.guild.id, f"censored:{count}", b, message.author.id)
                        if bucket is not None and await bucket.check(message.author.id, msg_time, 1, f"{message.channel.id}-{message.id}"):
                            count = await bucket.count(message.author.id, msg_time, expire=False)
                            period = await bucket.size(message.author.id, msg_time, expire=False) / 1000
                            self.bot.loop.create_task(
                                self.violate(Violation("max_censored", message.guild, f"{Translator.translate('spam_max_censored', message)} ({count}/{period}s)",
                                                       message.author,
                                                       message.channel,
                                                       await bucket.get(message.author.id, msg_time, expire=False),
                                                       b, count)))

            except CancelledError:
                pass
            except Exception as e:
                await TheRealGearBot.handle_exception("censor detector", self.bot, e)


    @staticmethod
    def assemble_reason(v):
        return Translator.translate('spam_infraction_reason', v.guild, channel=f"#{v.channel}",
                                    friendly=v.friendly)

    @staticmethod
    def is_exempt(guild_id, member: Member):
        if not hasattr(member, "roles"):
            return False
        config = Configuration.get_var(guild_id, "ANTI_SPAM")
        for role in member.roles:
            if role.id in config["EXEMPT_ROLES"]:
                return True
        return member.id in config["EXEMPT_USERS"] or Permissioncheckers.is_mod(member)

    @staticmethod
    def _get_mute_role(guild):
        role_id = Configuration.get_var(guild.id, "ROLES", "MUTE_ROLE")
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
