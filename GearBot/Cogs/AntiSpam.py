import asyncio
import datetime
import re
from asyncio import CancelledError
import hashlib

import disnake
import emoji

import time
from collections import deque

from disnake import Object, Forbidden, NotFound, RawMessageDeleteEvent
from disnake.channel import TextChannel
from disnake.ext import commands
from disnake.guild import Guild
from disnake.member import Member
from disnake.message import Message
from disnake.utils import snowflake_time

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
        self.count = count,


class ActionHolder:

    def __init__(self, count: int):
        self.count = count

EMOJI_REGEX = re.compile('([^<]*)<a?:(?:[^:]+):([0-9]+)>')
emoji_list = sorted(emoji.UNICODE_EMOJI.keys(), reverse=True)
class AntiSpam(BaseCog):

    def __init__(self, bot):
        super(AntiSpam, self).__init__(bot)
        # store values as functions so only what is needed is computed
        self.generators = {
            "max_messages": lambda m: 1,
            "max_newlines": lambda m: len(m.content.split("\n")) - 1,
            "max_mentions": lambda m: len(MENTION_MATCHER.findall(m.content)),
            "max_links": lambda m: len(URL_MATCHER.findall(m.content)),
            "max_emoji": lambda m: len([1 for c in m.content if c in emoji_list]) + len(EMOJI_REGEX.findall(m.content))
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
        self.processed = deque(maxlen=7500)
        self.censor_processed = deque(maxlen=7500)
        self.clean_processed = deque(maxlen=7500)
        self.running = True
        bot.loop.create_task(self.censor_detector())
        bot.loop.create_task(self.voice_spam_detector())


    def cog_unload(self):
        self.running = False


    def get_bucket(self, guild_id, rule_name, bucket_info):
        key = f"{guild_id}-{rule_name}"
        c = bucket_info.get("SIZE").get("COUNT")
        p = bucket_info.get("SIZE").get("PERIOD")
        return SpamBucket(self.bot.redis_pool, "{}:{}".format(key, "{}"), c, p)

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
        msg_time = int(message.created_at.timestamp())

        async def check_bucket(check, friendly_text, amount, b):
            # print(f"{check} - {amount}")
            if amount == 0:
                return

            bucket = self.get_bucket(message.guild.id, check, b)
            if bucket is not None and await bucket.check(message.author.id, msg_time, amount,
                                                         message=message.id, channel=message.channel.id,
                                                         user=message.author.id):
                count = await bucket.count(message.author.id, msg_time, expire=False)
                period = await bucket.size(message.author.id, msg_time, expire=False)
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
                await self.check_duplicates(message, bucket, True)
            elif t == "duplicates_across_users":
                await self.check_duplicates(message, bucket, False)
            else:
                v = 0
                if t in cache:
                    v = cache[t]
                elif t in self.generators:
                    v = self.generators[t](message)
                    cache[t] = v
                if v != 0:
                    await check_bucket(f"{t}:{message.author.id}", Translator.translate(f"spam_{t}", message), v,
                                       bucket)

    async def check_duplicates(self, message: Message, bucket, per_user):
        rule = bucket["SIZE"]
        full_content = message.content + "\n".join(str(a.filename) + str(a.content_type) for a in message.attachments) + "\n".join(str(sticker.id) for sticker in message.stickers)
        content_hash = f"{len(full_content)}.{hashlib.sha256(full_content.encode('utf-8')).hexdigest()}"
        if per_user:
            key = f"duplicates:{message.guild.id}:{message.author.id}:{'{}'}"
        else:
            key = f"duplicates:{message.guild.id}:{'{}'}"
        spam_bucket = SpamBucket(self.bot.redis_pool, key, rule["COUNT"], rule["PERIOD"])
        t = int(message.created_at.timestamp())
        if await spam_bucket.check(content_hash, t, 1, message=message.id, channel=message.channel.id,
                                   user=message.author.id):
            count = await spam_bucket.count(content_hash, t, expire=False)
            period = await spam_bucket.size(message.author.id, t, expire=False)
            st = Translator.translate('spam_max_duplicates', message)
            self.bot.loop.create_task(self.violate(Violation("max_duplicates", message.guild,
                                                             f"{st} ({count}/{period}s)",
                                                             message.author, message.channel,
                                                             await spam_bucket.get(content_hash, t, expire=False),
                                                             bucket, count)))


    async def violate(self, v: Violation):
        # deterining current punishment
        punish_info = v.bucket["PUNISHMENT"]
        t = punish_info["TYPE"]
        self.bot.dispatch('spam_violation', v)

        # Punish and Clean

        to_clean = AntiSpam._process_bucket_entries(v.offending_messages)
        by_channel = {}
        users = set()

        for (message, channel, user) in to_clean:
            m = int(message)
            if message == "0" or m in self.clean_processed:
                continue
            self.clean_processed.append(m)
            by_channel.setdefault(channel, []).append(message)
            member = await Utils.get_member(self.bot, v.guild, user, fetch_if_missing=True)
            if member is not None:
                users.add(member)

        for user in users:
            await self.punishments[t](v, user)
            if v.channel is not None:
                GearbotLogging.log_key(v.guild.id, 'spam_violate', user=Utils.clean_user(v.member), user_id=v.member.id,
                                       check=v.check.upper(), friendly=v.friendly, channel=v.channel.mention,
                                       punishment_type=t)
            else:
                GearbotLogging.log_key(v.guild.id, 'spam_violate_no_channel', user=Utils.clean_user(v.member),
                                       user_id=v.member.id,
                                       check=v.check.upper(), friendly=v.friendly, punishment_type=t)

        if v.bucket.get("CLEAN", True) and v.channel is not None:

            for (channel, msgs) in by_channel.items():
                guild_chan = v.guild.get_channel(int(channel))
                msgs = [Object(id=x) for x in msgs]
                if guild_chan is not None:
                    # Ensure we only delete 100 at a time. Probably not necessary but you never know with people
                    for group in Utils.chunks(msgs, 100):
                        try:
                            await guild_chan.delete_messages(group)
                        except NotFound:
                            pass
        await asyncio.sleep(v.bucket["SIZE"]["PERIOD"])

    async def warn_punishment(self, v: Violation, member):
        reason = v.bucket["PUNISHMENT"].get("REASON", self.assemble_reason(v))
        i = await InfractionUtils.add_infraction(v.guild.id, member.id, self.bot.user.id, 'Warn', reason)
        GearbotLogging.log_key(v.guild.id, 'warning_added_modlog', user=Utils.clean_user(member),
                               moderator=Utils.clean_user(v.guild.me), reason=reason,
                               user_id=member.id, moderator_id=v.guild.me.id, inf=i.id)
        await Utils.send_infraction(self.bot, member, v.guild, 'WARNING', 'warning', "Spam")


    async def mute_punishment(self, v: Violation, member):
        duration = v.bucket["PUNISHMENT"]["DURATION"]
        until = time.time() + duration
        reason = self.assemble_reason(v)
        role = AntiSpam._get_mute_role(v.guild)
        i = await Infraction.get_or_none(user_id = member.id, type = "Mute", guild_id = member.guild.id, active=True)
        if i is None:
            i = await InfractionUtils.add_infraction(v.guild.id, member.id, self.bot.user.id, 'Mute', reason,
                                               end=until)
            try:
                await member.add_roles(role, reason=reason)
            except Forbidden:
                GearbotLogging.log_key(v.guild.id, 'mute_punishment_failure',
                                       user=Utils.clean_user(member),
                                       user_id=member.id,
                                       duration=Utils.to_pretty_time(duration, v.guild.id),
                                       reason=reason, inf=i.id)
            else:
                GearbotLogging.log_key(v.guild.id, 'mute_log',
                                       user=Utils.clean_user(member),
                                       user_id=member.id,
                                       moderator=Utils.clean_user(v.guild.me),
                                       moderator_id=v.guild.me.id,
                                       duration=Utils.to_pretty_time(duration, v.guild.id),
                                       reason=reason, inf=i.id)
                if Configuration.get_var(v.guild.id, "INFRACTIONS", "DM_ON_MUTE"):
                    await Utils.send_infraction(self.bot, member, v.guild, 'MUTE', 'mute', reason, duration=Utils.to_pretty_time(duration, v.guild.id))
        else:
            i.end += duration
            i.reason += Utils.trim_message(f'+ {reason}', 2000)
            await i.save()
            GearbotLogging.log_key(v.guild.id, 'mute_duration_extended_log',
                                   user=Utils.clean_user(member),
                                   user_id=member.id,
                                   moderator=Utils.clean_user(v.guild.me),
                                   moderator_id=v.guild.me.id,
                                   duration=Utils.to_pretty_time(duration, v.guild.id),
                                   reason=reason, inf_id=i.id, end=i.end)
            InfractionUtils.clear_cache(v.guild.id)

        if member.voice:
            permissions = member.voice.channel.permissions_for(v.guild.me)
            if permissions.move_members:
                await member.move_to(None, reason=f"{reason}")

    async def kick_punishment(self, v: Violation, member):
        reason = self.assemble_reason(v)
        i = await InfractionUtils.add_infraction(v.guild.id, member.id, self.bot.user.id, 'Kick', reason,
                                           active=False)
        await self.bot.redis_pool.psetex(f"forced_exits:{v.guild.id}-{member.id}", 8000, "1")
        try:
            if Configuration.get_var(v.guild.id, "INFRACTIONS", "DM_ON_KICK"):
                asyncio.create_task(Utils.send_infraction(self.bot, member, v.guild, 'BOOT', 'kick', "Spam"))
            await v.guild.kick(member, reason=reason)
        except Forbidden:
            GearbotLogging.log_key(v.guild.id, 'kick_punishment_failure', user=Utils.clean_user(member), user_id=member.id,
                                   moderator=Utils.clean_user(v.guild.me), moderator_id=v.guild.me.id,
                                   reason=reason, inf=i.id)
        else:
            GearbotLogging.log_key(v.guild.id, 'kick_log', user=Utils.clean_user(member), user_id=member.id,
                                   moderator=Utils.clean_user(v.guild.me), moderator_id=v.guild.me.id,
                                   reason=reason, inf=i.id)

    async def temp_ban_punishment(self, v: Violation, member):
        reason = self.assemble_reason(v)
        duration = v.bucket["PUNISHMENT"]["DURATION"]
        until = time.time() + duration
        await self.bot.redis_pool.psetex(f"forced_exits:{v.guild.id}-{member.id}", 8000, 1)
        await v.guild.ban(member, reason=reason, delete_message_days=0)
        i = await InfractionUtils.add_infraction(v.guild.id, member.id, self.bot.user.id, 'Tempban', reason,
                                           end=until)
        if Configuration.get_var(v.guild.id, "INFRACTIONS", "DM_ON_TEMPBAN"):
            dur = Utils.to_pretty_time(duration, None)
            asyncio.create_task(Utils.send_infraction(self.bot, member, v.guild, 'BAN', 'tempban', "Spam", duration=dur))
        GearbotLogging.log_key(v.guild.id, 'tempban_log', user=Utils.clean_user(member),
                               user_id=member.id, moderator=Utils.clean_user(v.guild.me),
                               moderator_id=v.guild.me.id, reason=reason,
                               until=datetime.datetime.utcfromtimestamp(until).replace(tzinfo=datetime.timezone.utc), inf=i.id)

    async def ban_punishment(self, v: Violation, member):
        reason = self.assemble_reason(v)
        await self.bot.redis_pool.psetex(f"forced_exits:{v.guild.id}-{member.id}", 8000, 1)
        await v.guild.ban(member, reason=reason, delete_message_days=0)
        await Infraction.filter(user_id=member.id, type="Unban", guild_id=v.guild.id).update(active=False)
        i = await InfractionUtils.add_infraction(v.guild.id, member.id, self.bot.user.id, 'Ban', reason)
        GearbotLogging.log_key(v.guild.id, 'ban_log', user=Utils.clean_user(member), user_id=member.id,
                               moderator=Utils.clean_user(v.guild.me), moderator_id=v.guild.me.id,
                               reason=reason, inf=i.id)
        if Configuration.get_var(v.guild.id, "INFRACTIONS", "DM_ON_BAN"):
            asyncio.create_task(Utils.send_infraction(self.bot, member, v.guild, 'BAN', 'ban', "Spam"))



    async def censor_detector(self):
        # reciever task for someone gets censored
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
                        msg_time = int(snowflake_time(message.id).timestamp())
                        bucket = self.get_bucket(message.guild.id, "censored", b)
                        if bucket is not None and await bucket.check(message.author.id, msg_time, 1, message=message.id, channel=message.channel.id, user=message.author.id):
                            count = await bucket.count(message.author.id, msg_time, expire=False)
                            period = await bucket.size(message.author.id, msg_time, expire=False)
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

    async def voice_spam_detector(self):
        while self.running:
            try:
                member = None
                before = None
                after = None
                (member, before, after) = await self.bot.wait_for("voice_state_update")
                # make sure our cog is still running so we don't handle it twice
                if not self.running:
                    return

                # make sure anti-spam is enabled
                cfg = Configuration.get_var(member.guild.id, "ANTI_SPAM")
                if after.channel is None or before.channel == after.channel or member is None or not cfg.get("ENABLED", False) or self.is_exempt(member.guild.id, member):
                    continue
                buckets = Configuration.get_var(member.guild.id, "ANTI_SPAM", "BUCKETS", [])
                count = 0
                for b in buckets:
                    t = b["TYPE"]
                    if t == "voice_joins":
                        now = int(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).timestamp())
                        bucket = self.get_bucket(member.guild.id, f"voice_channel_join:{member.id}", b)
                        if bucket is not None and await bucket.check(member.id, now, message=now, channel=0, user=member.id, amount=1):
                            count = await bucket.count(member.id, now, expire=False)
                            period = await bucket.size(member.id, now, expire=False)
                            self.bot.loop.create_task(
                                self.violate(Violation("max_voice_joins", member.guild, f"{Translator.translate('spam_max_voice_join', member.guild)} ({count}/{period}s)",
                                                       member,
                                                       None,
                                                       set(),
                                                       b, count)))

            except CancelledError:
                pass
            except Exception as e:
                await TheRealGearBot.handle_exception("voice spam join detector", self.bot, e)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, data: RawMessageDeleteEvent):
        message = await MessageUtils.get_message_data(self.bot, data.message_id)
        if message is None:
            return  # can't do anything without the message data
        member = await Utils.get_member(self.bot, self.bot.get_guild(data.guild_id), message.author)
        if member is None:
            return  # user no longer present, probably already actioned
        if self.is_exempt(data.guild_id, member):
            return  # don't action except users

        if data.message_id in self.bot.deleted_messages and not Configuration.get_var("GENERAL", "BOT_DELETED_STILL_GHOSTS"):
            return

        ghost_message_threshold = Configuration.get_var(data.guild_id, "GENERAL", "GHOST_MESSAGE_THRESHOLD")
        ghost_ping_threshold = Configuration.get_var(data.guild_id, "GENERAL", "GHOST_PING_THRESHOLD")
        buckets = Configuration.get_var(data.guild_id, "ANTI_SPAM", "BUCKETS", [])
        mentions = len(MENTION_MATCHER.findall(message.content))

        msg_time = int(snowflake_time(message.messageid).timestamp())
        is_ghost = (snowflake_time(message.messageid) - datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)).total_seconds() < ghost_message_threshold
        is_ghost_ping = (snowflake_time(message.messageid) - datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)).total_seconds() < ghost_ping_threshold and mentions > 0

        if is_ghost or is_ghost_ping:
            for b in buckets:
                t = b["TYPE"]
                if t == "max_ghost_messages" and is_ghost:
                    now = int(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).timestamp())
                    bucket = self.get_bucket(member.guild.id, f"max_ghost_messages:{member.id}", b)
                    if bucket is not None and await bucket.check(member.id, now, message=message.messageid,
                                                                 channel=message.channel, user=message.author,
                                                                 amount=1):
                        count = await bucket.count(member.id, now, expire=False)
                        period = await bucket.size(member.id, now, expire=False)
                        self.bot.loop.create_task(
                            self.violate(Violation("max_ghost_messages", member.guild,
                                                   f"{Translator.translate('spam_max_ghost_messages', member.guild)} ({count}/{period}s)",
                                                   member,
                                                   self.bot.get_channel(data.channel_id),
                                                   await bucket.get(message.author, msg_time, expire=False),
                                                   b, count)))
                elif t == "max_ghost_pings" and is_ghost_ping:
                    bucket = self.get_bucket(member.guild.id, f"max_ghost_pings:{member.id}", b, )
                    if bucket is not None and await bucket.check(member.id, msg_time, message=message.messageid,
                                                                 channel=message.channel, user=message.author, amount=mentions):
                        count = await bucket.count(member.id, msg_time, expire=False)
                        period = await bucket.size(member.id, msg_time, expire=False)
                        self.bot.loop.create_task(
                            self.violate(Violation("max_ghost_pings", member.guild,
                                                   f"{Translator.translate('spam_max_ghost_pings', member.guild)} ({count}/{period}s)",
                                                   member,
                                                   self.bot.get_channel(data.channel_id),
                                                   await bucket.get(message.author, msg_time, expire=False),
                                                   b, count)))




    async def handle_failed_ping(self, message: disnake.Message, amount):
        if self.is_exempt(message.guild.id, message.author) or message.author.bot or message.webhook_id is not None:
            return  # don't action except users
        buckets = Configuration.get_var(message.guild.id, "ANTI_SPAM", "BUCKETS", [])
        msg_time = int(snowflake_time(message.id).timestamp())
        for b in buckets:
            t = b["TYPE"]
            if t == "max_failed_mass_pings":
                bucket = self.get_bucket(message.guild.id, f"max_failed_pings:{message.author.id}", b)
                if bucket is not None and await bucket.check(message.author.id, msg_time, message=message.id,
                                                             channel=message.channel.id, user=message.author.id,
                                                             amount=amount):
                    count = await bucket.count(message.author.id, msg_time, expire=False)
                    period = await bucket.size(message.author.id, msg_time, expire=False)
                    self.bot.loop.create_task(
                        self.violate(Violation("max_failed_pings", message.guild,
                                               f"{Translator.translate('spam_failed_pings', message.guild)} ({count}/{period}s)",
                                               message.author,
                                               message.channel,
                                               await bucket.get(message.author.id, msg_time, expire=False),
                                               b, count)))



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
        if role_id == 0:
            return None
        role = guild.get_role(role_id)
        return role

    @staticmethod
    def _process_bucket_entries(entries):
        def extract_re(key):
            parts = key.split("-")
            if len(parts) != 4:
                return None
            return parts[0], parts[1], parts[2]

        return set(filter(lambda x: x is not None, map(extract_re, entries)))


def setup(bot):
    bot.add_cog(AntiSpam(bot))
