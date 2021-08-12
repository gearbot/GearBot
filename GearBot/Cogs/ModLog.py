import asyncio
import collections
import datetime
import time

import discord
from discord import AuditLogAction, Role, DMChannel, MessageType, Thread, ChannelType
from discord.embeds import EmptyEmbed
from discord.ext import commands
from discord.raw_models import RawMessageDeleteEvent, RawMessageUpdateEvent, RawThreadDeleteEvent
from discord.utils import snowflake_time

from Cogs.BaseCog import BaseCog
from Util import GearbotLogging, Configuration, Utils, Archive, Emoji, Translator, InfractionUtils, Features, \
    MessageUtils
from Util.Matchers import ROLE_ID_MATCHER
from Util.Utils import assemble_jumplink
from database.DatabaseConnector import LoggedMessage, Infraction


class ModLog(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.running = True
        self.cache_message = None
        self.to_cache = []
        self.cache_start = 0
        self.clean_collector = dict()
        self.potential_unarchived = collections.deque(maxlen=50)

    def cog_unload(self):
        self.running = False

    async def buildCache(self, guild: discord.Guild, limit=None, startup=False):
        if limit is None:
            limit = 500 if startup else 50
        GearbotLogging.info(f"Populating modlog with missed messages during downtime for {guild.name} ({guild.id}).")
        newCount = 0
        editCount = 0
        count = 0
        no_access = 0
        for channel in guild.text_channels:
            permissions = channel.permissions_for(guild.get_member(self.bot.user.id))
            if permissions.read_messages and permissions.read_message_history:

                async for message in channel.history(limit=limit, oldest_first=False,
                                                     before=self.cache_message if startup else None):
                    if not self.running:
                        GearbotLogging.info("Cog unloaded while still building cache, aborting.")
                        return
                    logged = await LoggedMessage.get_or_none(messageid=message.id)
                    if logged is None:
                        await MessageUtils.insert_message(self.bot, message, redis=False)
                        newCount = newCount + 1
                    elif message.edited_at is not None:
                        if logged.content != message.content:
                            logged.content = message.content
                            await logged.save()
                            editCount = editCount + 1
                    count = count + 1
            else:
                no_access += 1
        GearbotLogging.info(
            f"Discovered {newCount} new messages and {editCount} edited in {guild.name} (checked {count})")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not hasattr(message.channel, "guild") or message.channel.guild is None:
            return
        if Configuration.get_var(message.guild.id, "MESSAGE_LOGS", "ENABLED") and (
                message.content != "" or len(message.attachments) > 0) and message.author.id != self.bot.user.id:
            await MessageUtils.insert_message(self.bot, message)
        failed_mass_ping = 0

        if "@everyone" in message.content and message.mention_everyone is False:
            failed_mass_ping += 1
        if "@here" in message.content and message.mention_everyone is False:
            failed_mass_ping += 1
        roles = ROLE_ID_MATCHER.findall(message.content)
        mentioned_roles = [str(role.id) for role in message.role_mentions]
        for role in roles:
            if role not in mentioned_roles:
                failed_mass_ping += 1

        if failed_mass_ping > 0:
            GearbotLogging.log_key(message.guild.id, "failed_mass_ping", user=Utils.clean_user(message.author),
                                   message=Utils.replace_lookalikes(message.content),
                                   link=assemble_jumplink(message.guild.id, message.channel.id, message.id))
            if self.bot.get_cog("AntiSpam") is not None:
                await self.bot.get_cog("AntiSpam").handle_failed_ping(message, failed_mass_ping)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, data: RawMessageDeleteEvent):
        if data.message_id in self.bot.deleted_messages:
            return
        c = self.bot.get_channel(data.channel_id)
        if c is None or isinstance(c, DMChannel) or c.guild is None or (
                not Features.is_logged(c.guild.id, "MESSAGE_LOGS")) or data.channel_id in Configuration.get_var(
            c.guild.id,
            "MESSAGE_LOGS",
            "IGNORED_CHANNELS_OTHER"):
            return
        message = await MessageUtils.get_message_data(self.bot, data.message_id)
        if message is not None:
            if message.channel in self.bot.being_cleaned:
                self.bot.being_cleaned[message.channel].add(data.message_id)
                return
            guild = self.bot.get_guild(message.server)
            user: discord.User = await Utils.get_user(message.author)
            hasUser = user is not None
            if not hasUser or user.id in Configuration.get_var(guild.id, "MESSAGE_LOGS",
                                                               "IGNORED_USERS") or user.id == guild.me.id:
                return
            channel = self.bot.get_channel(message.channel)
            name = Utils.clean_user(user) if hasUser else str(message.author)
            _time = Utils.to_pretty_time((datetime.datetime.utcnow().replace(
                tzinfo=datetime.timezone.utc) - snowflake_time(data.message_id)).total_seconds(), guild.id)
            with_id = Configuration.get_var(guild.id, "MESSAGE_LOGS", "MESSAGE_ID")
            reply_str = ""
            if message.reply_to is not None:
                reply_str = f"\n**{Translator.translate('in_reply_to', guild.id)}: **<{assemble_jumplink(guild.id, channel.id, message.reply_to)}>"
            GearbotLogging.log_key(guild.id, 'message_removed_with_id' if with_id else 'message_removed', name=name,
                                   user_id=user.id if hasUser else 'WEBHOOK', channel=channel.mention,
                                   message_id=data.message_id, time=_time.strip(), reply=reply_str)
            type_string = None
            if message.type is not None and message.type not in [MessageType.reply.value, MessageType.application_command.value, MessageType.thread_starter_message.value]:
                if message.type == MessageType.new_member.value:
                    type_string = Translator.translate('system_message_new_member', guild)
                elif message.type == MessageType.pins_add.value:
                    type_string = Translator.translate('system_message_new_pin', guild)
                else:
                    type_string = Translator.translate('system_message_unknown', guild)

                type_string = Translator.translate('system_message', guild, type=type_string)
            if Configuration.get_var(channel.guild.id, "MESSAGE_LOGS", "EMBED"):
                embed_content = type_string or message.content

                if len(embed_content) == 0:
                    embed_content = Translator.translate('no_content_embed', guild)

                embed = discord.Embed(
                    timestamp=datetime.datetime.utcfromtimestamp(time.time()).replace(tzinfo=datetime.timezone.utc),
                    description=embed_content)
                embed.set_author(name=user.name if hasUser else message.author,
                                 icon_url=user.avatar.url if hasUser else EmptyEmbed)

                embed.set_footer(text=Translator.translate('sent_in', guild, channel=channel.name))
                if len(message.attachments) > 0:
                    embed.add_field(name=Translator.translate('attachment_link', guild),
                                    value='\n'.join(
                                        Utils.assemble_attachment(channel.id, attachment.id, attachment.name) for
                                        attachment in message.attachments))
                GearbotLogging.log_raw(guild.id, "message_removed", embed=embed)
            else:
                if type_string is None:
                    if len(message.content) != 0:
                        cleaned_content = await Utils.clean(message.content, channel.guild)
                        GearbotLogging.log_raw(guild.id, 'message_removed',
                                               Translator.translate('content', guild.id, content=cleaned_content))
                else:
                    GearbotLogging.log_raw(guild.id, "message_removed", type_string)

                count = 1
                multiple_attachments = len(message.attachments) > 1
                for attachment in message.attachments:
                    attachment_url = Utils.assemble_attachment(channel.id, attachment.id, attachment.name)
                    if multiple_attachments:
                        attachment_str = Translator.translate('attachment_item', guild, num=count,
                                                              attachment=attachment_url)
                    else:
                        attachment_str = Translator.translate('attachment_single', guild, attachment=attachment_url)

                    GearbotLogging.log_raw(guild.id, "message_removed", attachment_str)
                    count += 1

    @commands.Cog.listener()
    async def on_raw_message_edit(self, event: RawMessageUpdateEvent):
        cid = int(event.data["channel_id"])
        if cid == Configuration.get_master_var("BOT_LOG_CHANNEL"):
            return
        c = self.bot.get_channel(cid)
        if c is None or isinstance(c, DMChannel) or c.guild is None or (
                not Features.is_logged(c.guild.id, "MESSAGE_LOGS")) or cid in Configuration.get_var(c.guild.id,
                                                                                                    "MESSAGE_LOGS",
                                                                                                    "IGNORED_CHANNELS_OTHER"):
            return
        message = await MessageUtils.get_message_data(self.bot, event.message_id)
        if message is not None and "content" in event.data:
            channel: discord.TextChannel = self.bot.get_channel(int(event.data["channel_id"]))
            if channel.guild is None:
                return
            user: discord.User = self.bot.get_user(message.author)
            hasUser = user is not None
            if message.content == event.data["content"]:
                # either pinned or embed data arrived, if embed data arrives it's gona be a recent one so we'll have the cached message to compare to
                old = message.pinned
                new = event.data["pinned"]
                if old == new:
                    return
                else:
                    parts = dict(channel=Utils.escape_markdown(c.name), channel_id=c.id)
                    if new:
                        # try to find who pinned it
                        key = "message_pinned"
                        m = await c.history(limit=5).get(type=MessageType.pins_add)
                        if m is not None:
                            key += "_by"
                            parts.update(user=Utils.escape_markdown(m.author), user_id=m.author.id)
                    else:
                        # impossible to determine who unpinned it :meowsad:
                        key = "message_unpinned"
                    GearbotLogging.log_key(c.guild.id, key, **parts)
                    GearbotLogging.log_raw(c.guild.id, key,
                                           f'```\n{Utils.trim_message(event.data["content"], 1990)}\n```')
                    GearbotLogging.log_raw(c.guild.id, key,
                                           f"{Translator.translate('jump_link', c.guild.id)}: {MessageUtils.construct_jumplink(c.guild.id, c.id, event.message_id)}")
                    await MessageUtils.update_message(self.bot, event.message_id, message.content, new)
                    return

            mc = message.content
            if mc is None or mc == "":
                mc = f"<{Translator.translate('no_content', channel.guild.id)}>"
            after = event.data["content"]
            if after is None or after == "":
                after = f"<{Translator.translate('no_content', channel.guild.id)}>"
            if hasUser and user.id not in Configuration.get_var(channel.guild.id, "MESSAGE_LOGS",
                                                                "IGNORED_USERS") and user.id != channel.guild.me.id:
                _time = Utils.to_pretty_time((datetime.datetime.utcnow().replace(
                    tzinfo=datetime.timezone.utc) - snowflake_time(message.messageid)).total_seconds(),
                                             channel.guild.id)
                with_id = Configuration.get_var(channel.guild.id, "MESSAGE_LOGS", "MESSAGE_ID")
                reply_str = ""
                if message.reply_to is not None:
                    reply_str = f"\n**{Translator.translate('in_reply_to', c.guild.id)}: **<{assemble_jumplink(c.guild.id, channel.id, message.reply_to)}>"
                GearbotLogging.log_key(channel.guild.id, 'edit_logging_with_id' if with_id else 'edit_logging',
                                       user=Utils.clean_user(user), user_id=user.id, channel=channel.mention,
                                       message_id=message.messageid, time=_time.strip(), reply=reply_str)
                if Configuration.get_var(channel.guild.id, "MESSAGE_LOGS", "EMBED"):
                    embed = discord.Embed()
                    embed.set_author(name=user if hasUser else message.author,
                                     icon_url=user.avatar.url if hasUser else EmptyEmbed)
                    embed.set_footer(
                        text=Translator.translate('sent_in', channel.guild.id, channel=f"#{channel.name}"))
                    embed.add_field(name=Translator.translate('before', channel.guild.id),
                                    value=Utils.trim_message(mc, 1024), inline=False)
                    embed.add_field(name=Translator.translate('after', channel.guild.id),
                                    value=Utils.trim_message(after, 1024), inline=False)
                    GearbotLogging.log_raw(channel.guild.id, "edit_logging", embed=embed)
                else:
                    clean_old = await Utils.clean(mc, channel.guild)
                    clean_new = await Utils.clean(after, channel.guild)
                    GearbotLogging.log_raw(channel.guild.id, "edit_logging", f"**Old:** {clean_old}")
                    GearbotLogging.log_raw(channel.guild.id, "edit_logging", f"**New:** {clean_new}")
            await MessageUtils.update_message(self.bot, event.message_id, after, event.data["pinned"])

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if Features.is_logged(member.guild.id, "TRAVEL_LOGS"):
            dif = (datetime.datetime.utcfromtimestamp(time.time()).replace(
                tzinfo=datetime.timezone.utc) - member.created_at)
            new_user_threshold = Configuration.get_var(member.guild.id, "GENERAL", "NEW_USER_THRESHOLD")
            minutes, seconds = divmod(dif.days * 86400 + dif.seconds, 60)
            hours, minutes = divmod(minutes, 60)
            age = (Translator.translate('days', member.guild.id,
                                        amount=dif.days)) if dif.days > 0 else Translator.translate('hours',
                                                                                                    member.guild.id,
                                                                                                    hours=hours,
                                                                                                    minutes=minutes)
            if new_user_threshold > dif.total_seconds():
                GearbotLogging.log_key(member.guild.id, 'join_logging_new', user=Utils.clean_user(member),
                                       user_id=member.id, age=age)
            else:
                GearbotLogging.log_key(member.guild.id, 'join_logging', user=Utils.clean_user(member),
                                       user_id=member.id, age=age)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.id == self.bot.user.id: return
        timestamp = datetime.datetime.utcnow()
        if await self.bot.redis_pool.get(f"forced_exits:{member.guild.id}-{member.id}") is not None:
            return
        await asyncio.sleep(4)
        if member.guild.me is not None and member.guild.me.guild_permissions.view_audit_log and Features.is_logged(
                member.guild.id, "MOD_ACTIONS"):
            try:
                async for entry in member.guild.audit_logs(limit=25):
                    if entry.action not in (AuditLogAction.kick, AuditLogAction.ban):
                        continue
                    if member.joined_at is None or member.joined_at > entry.created_at or entry.created_at < datetime.datetime.utcfromtimestamp(
                            time.time() - 30).replace(tzinfo=datetime.timezone.utc):
                        break
                    if entry.target == member:
                        if entry.reason is None:
                            reason = Translator.translate("no_reason", member.guild.id)
                        else:
                            reason = entry.reason
                        inf_type = "Kick" if entry.action == AuditLogAction.kick else "Ban"
                        i = await InfractionUtils.add_infraction(member.guild.id, entry.target.id, entry.user.id,
                                                                 inf_type, reason,
                                                                 active=False)
                        GearbotLogging.log_key(member.guild.id, f'{inf_type.lower()}_log',
                                               user=Utils.clean_user(member), user_id=member.id,
                                               moderator=Utils.clean_user(entry.user), moderator_id=entry.user.id,
                                               reason=reason, inf=i.id, timestamp=timestamp)
                        return
                    await asyncio.sleep(2)
            except discord.Forbidden:
                permissions = member.guild.me.guild_permissions
                perm_info = ", ".join(f"{name}: {value}" for name, value in permissions)
                await GearbotLogging.bot_log(
                    f"{Emoji.get_chat_emoji('WARNING')} Tried to fetch audit log for {member.guild.name} ({member.guild.id}) but got denied even though it said i have access, guild permissions: ```{perm_info}```")

        if Features.is_logged(member.guild.id, "TRAVEL_LOGS"):
            GearbotLogging.log_key(member.guild.id, 'leave_logging', user=Utils.clean_user(member), user_id=member.id,
                                   timestamp=timestamp)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if user.id == self.bot.user.id or not Features.is_logged(guild.id, "MOD_ACTIONS"):
            return
        timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        if guild.me.guild_permissions.view_audit_log:
            return

        if await self.bot.redis_pool.get(f"forced_exits:{guild.id}-{user.id}") is not None:
            return

        await self.bot.redis_pool.psetex(f"forced_exits:{guild.id}-{user.id}", 8000, "1")
        await Infraction.filter(user_id=user.id, type="Unban", guild_id=guild.id).update(active=False)
        i = await InfractionUtils.add_infraction(guild.id, user.id, 0, "Ban", "Manual ban")
        GearbotLogging.log_key(guild.id, 'manual_ban_log', user=Utils.clean_user(user), user_id=user.id, inf=i.id,
                               timestamp=timestamp)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        fid = f"{guild.id}-{user.id}"
        if fid in self.bot.data["unbans"]:
            self.bot.data["unbans"].remove(fid)
            return
        elif not Features.is_logged(guild.id, "MOD_ACTIONS"):
            return
        timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        await Infraction.filter(user_id=user.id, type="Ban", guild_id=guild.id).update(active=False)

        limit = datetime.datetime.utcfromtimestamp(time.time() - 60).replace(tzinfo=datetime.timezone.utc)
        log = await self.find_log(guild, AuditLogAction.unban, lambda e: e.target == user and e.created_at > limit)
        if log is None:
            # this fails way to often for my liking, alternative is adding a delay but this seems to do the trick for now
            log = await self.find_log(guild, AuditLogAction.unban, lambda e: e.target == user and e.created_at > limit)
        if log is not None:
            i = await InfractionUtils.add_infraction(guild.id, user.id, log.user.id, "Unban", "Manual unban")
            GearbotLogging.log_key(guild.id, 'unban_log', user=Utils.clean_user(user), user_id=user.id,
                                   moderator=log.user, moderator_id=log.user.id, reason='Manual unban', inf=i.id,
                                   timestamp=timestamp)


        else:
            i = await InfractionUtils.add_infraction(guild.id, user.id, 0, "Unban", "Manual ban")
            GearbotLogging.log_key(guild.id, 'manual_unban_log', user=Utils.clean_user(user), user_id=user.id, inf=i.id,
                                   timestamp=timestamp)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after):
        guild = before.guild
        timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        # nickname changes
        if Features.is_logged(guild.id, "NAME_CHANGES"):
            if (before.nick != after.nick and
                after.nick != before.nick) and f'{before.guild.id}-{before.id}' not in self.bot.data[
                'nickname_changes']:
                name = Utils.clean_user(after)
                before_clean = "" if before.nick is None else Utils.clean_name(before.nick)
                after_clean = "" if after.nick is None else Utils.clean_name(after.nick)
                entry = await self.find_log(guild, AuditLogAction.member_update,
                                            lambda e: e.target.id == before.id and hasattr(e.changes.before,
                                                                                           "nick") and hasattr(
                                                e.changes.after,
                                                "nick") and before.nick == e.changes.before.nick and after.nick == e.changes.after.nick and e.created_at > datetime.datetime.utcfromtimestamp(
                                                time.time() - 2).replace(tzinfo=datetime.timezone.utc))
                if before.nick is None:
                    type = "added"
                elif after.nick is None:
                    type = "removed"
                else:
                    type = "changed"
                mod_name = ""
                mod_id = ""
                if entry is None:
                    actor = "unknown"
                elif entry.target.id == entry.user.id:
                    actor = "own"
                else:
                    mod_name = Utils.clean_user(entry.user)
                    mod_id = entry.user.id
                    actor = "mod"
                GearbotLogging.log_key(guild.id, f'{actor}_nickname_{type}', user=name, user_id=before.id,
                                       before=before_clean, after=after_clean, moderator=mod_name, moderator_id=mod_id,
                                       timestamp=timestamp)

        # role changes
        if Features.is_logged(guild.id, "ROLE_CHANGES"):
            removed = []
            added = []
            for role in before.roles:
                if role not in after.roles:
                    removed.append(role)

            for role in after.roles:
                if role not in before.roles:
                    added.append(role)

            if (len(removed) + len(added)) > 0:
                entry = await self.find_log(guild, AuditLogAction.member_role_update,
                                            lambda e: e.target.id == before.id and hasattr(e.changes.before,
                                                                                           "roles") and hasattr(
                                                e.changes.after, "roles") and all(
                                                r in e.changes.before.roles for r in removed) and all(
                                                r in e.changes.after.roles for r in
                                                added) and e.created_at > datetime.datetime.utcfromtimestamp(
                                                time.time() - 1).replace(tzinfo=datetime.timezone.utc))
                if entry is not None:
                    removed = entry.changes.before.roles
                    added = entry.changes.after.roles
                    for role in removed:
                        GearbotLogging.log_key(guild.id, 'role_removed_by', role=role.name,
                                               user=Utils.clean_user(entry.target), user_id=entry.target.id,
                                               moderator=Utils.clean_user(entry.user), moderator_id=entry.user.id,
                                               timestamp=timestamp)
                    for role in added:
                        GearbotLogging.log_key(guild.id, 'role_added_by', role=role.name,
                                               user=Utils.clean_user(entry.target), user_id=entry.target.id,
                                               moderator=Utils.clean_user(entry.user), moderator_id=entry.user.id,
                                               timestamp=timestamp)
                else:
                    for role in removed:
                        GearbotLogging.log_key(guild.id, 'role_removed', role=role.name, user=Utils.clean_user(before),
                                               user_id=before.id, timestamp=timestamp)
                    for role in added:
                        GearbotLogging.log_key(guild.id, 'role_added', role=role.name, user=Utils.clean_user(before),
                                               user_id=before.id, timestamp=timestamp)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after):
        # Username and discriminator changes
        if before.name != after.name or before.discriminator != after.discriminator:
            for guild in self.bot.guilds:
                if guild.get_member(before.id) is not None:
                    after_clean_name = Utils.escape_markdown(Utils.replace_lookalikes(after.name))
                    GearbotLogging.log_key(guild.id, 'username_changed', after_clean=after_clean_name, before=before,
                                           user_id=after.id, after=after)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if Features.is_logged(member.guild.id, "VOICE_CHANGES_DETAILED"):
            simple = ["deaf", "mute", "self_mute", "self_deaf", "afk"]
            for s in simple:
                old = getattr(before, s)
                new = getattr(after, s)
                if old != new:
                    key = f"voice_change_{s}_{str(new).lower()}"
                    GearbotLogging.log_key(member.guild.id, key, user=Utils.clean_user(member), user_id=member.id)
        if Features.is_logged(member.guild.id, "VOICE_CHANGES"):
            if before.channel != after.channel:
                parts = dict(user=Utils.clean_user(member), user_id=member.id)
                if before.channel is None:
                    key = "connected_to_voice"
                    parts.update(channel_name=after.channel.name, channel_id=after.channel.id)
                elif after.channel is None:
                    key = "disconnected_voice"
                    parts.update(channel_name=before.channel.name, channel_id=before.channel.id)
                else:
                    key = "moved_voice"
                    parts.update(old_channel_name=before.channel.name, old_channel_id=before.channel.id,
                                 new_channel_name=after.channel.name, new_channel_id=after.channel.id)
                GearbotLogging.log_key(member.guild.id, key, **parts)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, event: discord.RawBulkMessageDeleteEvent):
        if Features.is_logged(event.guild_id, "MESSAGE_LOGS"):
            if event.channel_id in Configuration.get_var(event.guild_id, "MESSAGE_LOGS", "IGNORED_CHANNELS_OTHER"):
                return
            if event.channel_id in self.bot.being_cleaned:
                for mid in event.message_ids:
                    self.bot.being_cleaned[event.channel_id].add(mid)
                return
            message_list = dict()
            for mid in event.message_ids:
                message = await MessageUtils.get_message_data(self.bot, mid)
                if message is not None:
                    message_list[mid] = message
            if len(message_list) > 0:
                await Archive.archive_purge(self.bot, event.guild_id,
                                            collections.OrderedDict(sorted(message_list.items())))

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.guild is not None and Features.is_logged(ctx.guild.id, "MISC"):
            clean_content = await Utils.clean(ctx.message.content, ctx.guild, markdown=False, links=False, emoji=False)
            GearbotLogging.log_key(ctx.guild.id, 'command_used', user=Utils.escape_markdown(ctx.author),
                                   user_id=ctx.author.id, channel=ctx.message.channel.mention,
                                   tag_on=f"`{Utils.trim_message(clean_content, 1996)}`")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if not Features.is_logged(channel.guild.id, "CHANNEL_CHANGES"): return
        timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        e = await self.find_log(channel.guild, AuditLogAction.channel_create, lambda e: e.target.id == channel.id)
        if e is not None:
            GearbotLogging.log_key(channel.guild.id, 'channel_created_by', channel=channel.name, channel_id=channel.id,
                                   person=Utils.clean_user(e.user), person_id=e.user.id, timestamp=timestamp)
        else:
            GearbotLogging.log_key(channel.guild.id, "channel_created", channel=channel.name, channel_id=channel.id,
                                   timestamp=timestamp)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not Features.is_logged(channel.guild.id, "CHANNEL_CHANGES"): return
        timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        e = await self.find_log(channel.guild, AuditLogAction.channel_delete, lambda e: e.target.id == channel.id)
        if e is not None:
            GearbotLogging.log_key(channel.guild.id, "channel_deleted_by", channel=channel.name, channel_id=channel.id,
                                   person=Utils.clean_user(e.user), person_id=e.user.id, timestamp=timestamp)
        else:
            GearbotLogging.log_key(channel.guild.id, "channel_deleted", channel=channel.name, channel_id=channel.id,
                                   timestamp=timestamp)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if not Features.is_logged(before.guild.id, "CHANNEL_CHANGES") or before.id in Configuration.get_var(
                before.guild.id, "MESSAGE_LOGS", "IGNORED_CHANNELS_CHANGES"): return
        timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        await self.handle_simple_changes(before, after, "channel_update_simple",
                                         AuditLogAction.channel_update,
                                         ["name", "category", "nsfw", "slowmode_delay", "topic", "bitrate",
                                          "user_limit", "type"], timestamp)

        # checking overrides

        if len(before.overwrites) > 25 or len(after.overwrites) > 25:
            return
        for target, override in before.overwrites.items():
            if target in after.overwrites:
                # still exists, check for modifications
                a_override = after.overwrites[target]
                if override._values != a_override._values:
                    # something changed
                    for perm, value in override:
                        new_value = getattr(a_override, perm)
                        if value != new_value:
                            parts = dict(before=self.prep_override(value), after=self.prep_override(new_value),
                                         permission=perm, channel=Utils.escape_markdown(after), channel_id=after.id,
                                         target_name=Utils.escape_markdown(str(target)), target_id=target.id)
                            key = "permission_override_update"

                            def finder(e):
                                if e.target.id == after.id and e.target.id == after.id and e.extra.id == target.id and target in after.overwrites:
                                    before_allowed, before_denied = override.pair()
                                    after_allowed, after_denied = after.overwrites[target].pair()
                                    has_allow = hasattr(e.before, "allow")
                                    has_deny = hasattr(e.before, "deny")
                                    if not (((has_allow and (
                                            before_allowed.value != after_allowed.value) and before_allowed.value == e.before.allow.value and after_allowed.value == e.after.allow.value) or (
                                                     has_allow == hasattr(e.after, "allow")))
                                            and ((has_deny and (
                                                    before_denied.value != before_denied.value) and before_denied.value == e.before.deny.value and after_denied.value == e.after.deny.value) or has_deny == hasattr(
                                                e.after, "deny"))):
                                        return False
                                    return True
                                return False

                            entry = await self.find_log(after.guild, AuditLogAction.overwrite_update, finder)
                            if isinstance(target, Role):
                                key += "_role"
                            if entry is not None:
                                key += "_by"
                                parts.update(person=Utils.clean_user(entry.user), person_id=entry.user.id)
                            GearbotLogging.log_key(after.guild.id, key, timestamp=timestamp, **parts)
            else:
                # permission override removed
                key = "permission_override_removed"
                parts = dict(channel=Utils.escape_markdown(after), channel_id=after.id,
                             target_name=Utils.escape_markdown(str(target)), target_id=target.id)

                def finder(e):
                    if e.target.id == after.id and e.extra.id == target.id:
                        before_allowed, before_denied = override.pair()
                        has_allow = hasattr(e.before, "allow")
                        has_deny = hasattr(e.before, "deny")
                        if not ((has_allow and before_allowed.value == e.before.allow.value) or (
                                (not has_allow) and before_allowed.value == 0)
                                and (has_deny and before_denied.value == e.before.deny.value) or (
                                        (not has_deny) and before_denied.value == 0)):
                            return False
                        return True

                entry = await self.find_log(after.guild, AuditLogAction.overwrite_delete, finder)
                if isinstance(target, Role):
                    key += "_role"
                if entry is not None:
                    key += "_by"
                    parts.update(person=Utils.clean_user(entry.user), person_id=entry.user.id)
                GearbotLogging.log_key(after.guild.id, key, timestamp=timestamp, **parts)

        for target in set(after.overwrites.keys()).difference(before.overwrites.keys()):
            key = "permission_override_added"
            parts = dict(channel=Utils.escape_markdown(after), channel_id=after.id,
                         target_name=Utils.escape_markdown(str(target)), target_id=target.id)

            def finder(e):
                if e.target.id == after.id and e.extra.id == target.id and target in after.overwrites:
                    after_allowed, after_denied = after.overwrites[target].pair()
                    has_allow = hasattr(e.after, "allow")
                    has_deny = hasattr(e.after, "deny")
                    if not ((has_allow and after_allowed.value == e.after.allow.value) or (
                            (not has_allow) and after_allowed.value == 0)
                            and (has_deny and after_denied.value == e.after.deny.value) or (
                                    (not has_deny) and after_denied.value == 0)):
                        return False
                    return True

            entry = await self.find_log(after.guild, AuditLogAction.overwrite_create, finder)
            if isinstance(target, Role):
                key += "_role"
            if entry is not None:
                key += "_by"
                parts.update(person=Utils.clean_user(entry.user), person_id=entry.user.id)
            GearbotLogging.log_key(after.guild.id, key, timestamp=timestamp, **parts)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        if not Features.is_logged(role.guild.id, "ROLE_CHANGES"): return
        timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        entry = await self.find_log(role.guild, AuditLogAction.role_create, lambda e: e.target.id == role.id)
        if entry is None:
            GearbotLogging.log_key(role.guild.id, 'role_created', role=role.name, timestamp=timestamp)
        else:
            GearbotLogging.log_key(role.guild.id, 'role_created_by', role=role.name,
                                   person=Utils.clean_user(entry.user), person_id=entry.user.id, timestamp=timestamp)

    async def on_guild_role_delete(self, role: discord.Role):
        if not Features.is_logged(role.guild.id, "ROLE_CHANGES"): return
        timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        entry = await self.find_log(role.guild, AuditLogAction.role_delete, lambda e: e.target.id == role.id,
                                    timestamp=timestamp)
        if entry is None:
            GearbotLogging.log_key(role.guild.id, 'role_deleted', role=role.name)
        else:
            GearbotLogging.log_key(role.guild.id, 'role_deleted_by', role=role.name,
                                   person=Utils.clean_user(entry.user), person_id=entry.user.id, timestamp=timestamp)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after):
        if not Features.is_logged(before.guild.id, "ROLE_CHANGES"): return
        timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        await self.handle_simple_changes(before, after, "role_update_simple", AuditLogAction.role_update,
                                         ["name", "color", "hoist", "mentionable"], timestamp)
        if before.permissions != after.permissions:
            for perm, value in before.permissions:
                av = getattr(after.permissions, perm)
                if av != value:
                    entry = await self.find_log(before.guild, AuditLogAction.role_update,
                                                lambda e: e.target.id == after.id and hasattr(e.before,
                                                                                              "permissions") and e.before.permissions == before.permissions and e.after.permissions == after.permissions)
                    key = f"role_update_perm_{'added' if av else 'revoked'}"
                    parts = dict(role=await Utils.clean(after.name), role_id=after.id, perm=perm)
                    if entry is not None:
                        key += "_by"
                        parts.update(person=Utils.clean_user(entry.user), person_id=entry.user.id)
                    GearbotLogging.log_key(after.guild.id, key, **parts, timestamp=timestamp)

    async def handle_simple_changes(self, before, after, base_key, action, attributes, timestamp):
        for attr in attributes:
            if hasattr(before, attr):
                ba = getattr(before, attr)
                if isinstance(ba, str) and ba.strip() == "":
                    ba = None
                aa = getattr(after, attr)
                if isinstance(aa, str) and aa.strip() == "":
                    aa = None
                key = base_key
                if ba != aa:
                    entry = await self.find_log(before.guild, action,
                                                lambda
                                                    e: e.target is not None and e.changes is not None and e.target.id == before.id and hasattr(
                                                    e.changes.before, attr) and getattr(e.changes.before,
                                                                                        attr) == ba and getattr(
                                                    e.changes.after, attr) == aa)
                    parts = dict(before=self.prep_attr(ba), after=self.prep_attr(aa), thing=after, thing_id=after.id,
                                 attr=attr)
                    if entry is not None:
                        parts.update(person=entry.user, person_id=entry.user.id)
                        key += "_by"
                    GearbotLogging.log_key(before.guild.id, key, timestamp=timestamp, **parts)

    @commands.Cog.listener()
    async def on_raw_thread_create(self, thread: Thread):
        if thread.archive_timestamp < (
                datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) - datetime.timedelta(minutes=1)):
            return
        t = self.convert_thread_type(thread.guild.id, thread.type)
        entry = await self.find_log(thread.guild, AuditLogAction.thread_create,
                                    lambda e: e.target is not None and e.target.id == thread.id)
        if entry is not None:
            GearbotLogging.log_key(thread.guild.id, "thread_created_by_user", channel=thread.parent.name,
                                   channel_id=thread.parent_id, owner=Utils.clean_user(entry.user),
                                   owner_id=entry.user.id, thread=thread.name, thread_id=thread.id,
                                   type=t)
        else:
            GearbotLogging.log_key(thread.guild.id, "thread_created", channel=thread.parent.name,
                                   channel_id=thread.parent_id, thread=thread.name,
                                   thread_id=thread.id, type=t)

    @commands.Cog.listener()
    async def on_raw_thread_delete(self, raw: RawThreadDeleteEvent):
        guild = self.bot.get_guild(raw.guild_id)
        if guild is None:
            return
        t = self.convert_thread_type(raw.guild_id, raw.thread_type)
        entry = await self.find_log(guild, AuditLogAction.thread_delete,
                                    lambda e: e.target is not None and e.target.id == raw.thread_id)
        if entry is not None:

            if raw.thread is not None:
                channel = self.bot.get_channel(raw.thread.parent_id)
                if channel is not None:
                    GearbotLogging.log_key(guild.id, "thread_deleted_by_user", channel=channel.name,
                                           channel_id=raw.thread.parent_id, user=Utils.clean_user(entry.user),
                                           user_id=entry.user.id, thread=raw.thread.name, thread_id=raw.thread_id, type=t)
            else:
                GearbotLogging.log_key(guild.id, "thread_unknown_channel_deleted_by_user",
                                       user=Utils.clean_user(entry.user),
                                       user_id=entry.user.id, thread_id=raw.thread_id, type=t)
        else:
            if raw.thread is not None:
                channel = self.bot.get_channel(raw.thread.parent_id)
                if channel is not None:
                    GearbotLogging.log_key(guild.id, "thread_deleted", channel=channel.name,
                                           channel_id=raw.thread.parent_id, thread=raw.thread.name, thread_id=raw.thread_id,
                                           type=t)
            else:
                GearbotLogging.log_key(guild.id, "thread_unknown_channel_deleted", thread_id=raw.thread_id, type=t)

    @commands.Cog.listener()
    async def on_raw_thread_update(self, thread: discord.Thread):
        if hasattr(thread, "archived") and thread.archived is False:
            self.potential_unarchived.append(thread.id)
            await asyncio.sleep(0.5)
            if thread.id in self.potential_unarchived:
                self.potential_unarchived.remove(thread.id)
                await self.unarchived_thread(thread)

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        if after.id in self.potential_unarchived:
            self.potential_unarchived.remove(after.id)

        t = self.convert_thread_type(after.guild.id, after.type)
        if before.archived and not after.archived:
            await self.unarchived_thread(after)

        if not before.archived and after.archived:
            planned_archive = discord.utils.snowflake_time(after.last_message_id if after.last_message_id is not None else after.id) + datetime.timedelta(
                minutes=after.auto_archive_duration) - datetime.timedelta(
                seconds=1)  # somehow this sometimes seems to be off by a second
            if after.archive_timestamp >= planned_archive:
                GearbotLogging.log_key(after.guild.id, f"thread_auto_archived", thread_id=after.id, type=t,
                                       channel_id=after.parent_id,
                                       duration=Utils.to_pretty_time(after.auto_archive_duration * 60, after.guild.id))
            elif not after.locked:
                GearbotLogging.log_key(after.guild.id, f"thread_archived_by_owner", thread_id=after.id, type=t,
                                       channel_id=after.parent_id)
            else:
                entry = await self.find_log(after.guild, AuditLogAction.thread_update,
                                            lambda e: e.target is not None and e.target.id == after.id and
                                                      hasattr(e.changes.after, "archived") and
                                                      e.changes.after.archived is True)
                if entry is not None:
                    GearbotLogging.log_key(after.guild.id, "thread_archived_by_mod", thread_id=after.id, type=t,
                                           channel_id=after.parent_id, user=Utils.clean_user(entry.user),
                                           user_id=entry.user.id)
                else:
                    GearbotLogging.log_key(after.guild.id, "thread_archived_mod", thread_id=after.id, type=t,
                                           channel_id=after.parent_id)

        timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        await self.handle_simple_changes(before, after, "thread_update_simple",
                                         AuditLogAction.thread_update,
                                         ["name", "slowmode_delay", "auto_archive_duration"], timestamp)

    async def unarchived_thread(self, thread: discord.Thread):
        t = self.convert_thread_type(thread.guild.id, thread.type)
        entry = await self.find_log(thread.guild, AuditLogAction.thread_update,
                                    lambda
                                        e: e.target is not None and e.changes is not None and e.target.id == thread.id and hasattr(
                                        e.changes.after,
                                        "archived") and e.changes.after.archived is False)
        if entry is not None:
            GearbotLogging.log_key(thread.guild.id, "thread_unarchived_by", thread_id=thread.id, type=t,
                                   channel_id=thread.parent_id, user=Utils.clean_user(entry.user),
                                   user_id=entry.user.id)
        else:
            GearbotLogging.log_key(thread.guild.id, "thread_unarchived", thread_id=thread.id, type=t,
                                   channel_id=thread.parent_id)

    @commands.Cog.listener()
    async def on_thread_member_join(self, thread_member: discord.ThreadMember):
        member = await Utils.get_member(self.bot, thread_member.parent.guild, thread_member.id, fetch_if_missing=True)
        if member is not None:
            GearbotLogging.log_key(thread_member.thread.guild.id, "thread_member_add", user=Utils.clean_user(member),
                                   user_id=thread_member.id, thread_id=thread_member.thread_id,
                                   channel_id=thread_member.thread.parent_id)

    @commands.Cog.listener()
    async def on_raw_thread_member_remove(self, thread: discord.Thread, member_id):
        member = await Utils.get_member(self.bot, thread.guild, member_id, fetch_if_missing=True)
        if member is not None:
            GearbotLogging.log_key(thread.guild.id, "thread_member_remove", user=Utils.clean_user(member),
                                   user_id=member.id, thread_id=thread.id, channel_id=thread.parent_id)

    @staticmethod
    def convert_thread_type(guild_id, t):
        k = "public" if t == ChannelType.public_thread else "private"
        return Translator.translate(k, guild_id)

    @staticmethod
    def prep_attr(attr):
        attr = f"\u200b{Utils.trim_message(str(attr), 900)}\u200b"
        if "\n" in attr:
            return f"`{attr}`"
        return attr

    @staticmethod
    def prep_override(value):
        if value is None:
            return "neutral"
        elif value is False:
            return "denied"
        elif value is True:
            return "granted"

    @staticmethod
    async def find_log(guild, action, matcher, check_limit=10, retry=True):
        try:
            return await asyncio.wait_for(find_actual_log(guild, action, matcher, check_limit, retry), 10)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            return None


async def find_actual_log(guild, action, matcher, check_limit, retry):
    try:
        if guild.me is None:
            return None
        entry = None
        if guild.me.guild_permissions.view_audit_log:
            try:
                async for e in guild.audit_logs(action=action, limit=check_limit):
                    if matcher(e):
                        if entry is None or e.id > entry.id:
                            entry = e
            except discord.Forbidden:
                pass
        if entry is None and retry:
            await asyncio.sleep(2)
            return await ModLog.find_log(guild, action, matcher, check_limit, False)
        if entry is not None and isinstance(entry.target, discord.Object):
            entry.target = await Utils.get_user(entry.target.id)
        return entry
    except (asyncio.TimeoutError, asyncio.CancelledError):
        return None


def setup(bot):
    bot.add_cog(ModLog(bot))
