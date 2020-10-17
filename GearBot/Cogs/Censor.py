import re
from urllib import parse
from urllib.parse import urlparse

import discord
import emoji
from discord import DMChannel
from discord.ext import commands

from Cogs.BaseCog import BaseCog
from Util import Configuration, GearbotLogging, Permissioncheckers, Utils, MessageUtils
from Util.Matchers import INVITE_MATCHER, URL_MATCHER

EMOJI_REGEX = re.compile('([^<]*)<a?:(?:[^:]+):([0-9]+)>')
class Censor(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.regexes = dict()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.webhook_id is not None or message.channel is None or isinstance(message.channel, DMChannel) or not Configuration.get_var(message.channel.guild.id, "CENSORING", "ENABLED") or self.bot.user.id == message.author.id:
            return
        member = message.guild.get_member(message.author.id) #d.py is weird
        if member is None:
            return
        await self.check_message(member, message.content, message.channel, message.id)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, event: discord.RawMessageUpdateEvent):
        channel = self.bot.get_channel(int(event.data["channel_id"]))
        m = await MessageUtils.get_message_data(self.bot, event.message_id)
        if channel is None or isinstance(channel, DMChannel) or not Configuration.get_var(channel.guild.id, "CENSORING", "ENABLED") or "content" not in event.data:
            return
        author_id=None
        if m is not None:
            author_id = m.author
        else:
            permissions = channel.permissions_for(channel.guild.me)
            if permissions.read_messages and permissions.read_message_history:
                try:
                    message = await channel.fetch_message(event.message_id)
                except (discord.NotFound, discord.Forbidden): # we should never get forbidden, be we do, somehow
                    return
                else:
                    author_id = message.author.id

        member = channel.guild.get_member(author_id)
        if member is not None and author_id != self.bot.user.id:
            await self.check_message(member, event.data["content"], channel, event.message_id)

    async def check_message(self, member, content, channel, message_id):
        if Permissioncheckers.get_user_lvl(member.guild, member) >= 2:
            return
        censorlist = Configuration.get_var(member.guild.id, "CENSORING", "TOKEN_CENSORLIST")
        word_censorlist = Configuration.get_var(member.guild.id, "CENSORING", "WORD_CENSORLIST")
        guilds = Configuration.get_var(member.guild.id, "CENSORING", "ALLOWED_INVITE_LIST")
        domain_list = Configuration.get_var(member.guild.id, "CENSORING", "DOMAIN_LIST")
        domains_allowed = Configuration.get_var(member.guild.id, "CENSORING", "DOMAIN_LIST_ALLOWED")
        full_message_list = Configuration.get_var(member.guild.id, "CENSORING", "FULL_MESSAGE_LIST")
        censor_emoji_message = Configuration.get_var(member.guild.id, "CENSORING", "CENSOR_EMOJI_ONLY_MESSAGES")
        content = content.replace('\\', '')
        decoded_content = parse.unquote(content)

        if len(guilds) is not 0:
            codes = INVITE_MATCHER.findall(decoded_content)
            for code in codes:
                try:
                    invite: discord.Invite = await self.bot.fetch_invite(code)
                except discord.NotFound:
                    await self.censor_invite(member, message_id, channel, code, "INVALID INVITE", content)
                    return
                if invite.guild is None:
                    await self.censor_invite(member, message_id, channel, code, "DM group", content)
                    return
                else:
                    if invite.guild is None or (not invite.guild.id in guilds and invite.guild.id != member.guild.id):
                        await self.censor_invite(member, message_id, channel, code, invite.guild.name, content)
                        return

        content = content.lower()

        if content in full_message_list:
            await self.censor_message(message_id, content, channel, member, "", "_content")
            return

        for bad in (w.lower() for w in censorlist):
            if bad in content:
                await self.censor_message(message_id, content, channel, member, bad)
                return

        if len(word_censorlist) > 0:
            if channel.guild.id not in self.regexes:
                regex = re.compile(r"\b(" + '|'.join(re.escape(word) for word in word_censorlist) + r")\b", re.IGNORECASE)
                self.regexes[channel.guild.id] = regex
            else:
                regex = self.regexes[channel.guild.id]
            match = regex.findall(content)
            if len(match):
                await self.censor_message(message_id, content, channel, member, match[0], "_word")
                return

        if len(domain_list) > 0:
            link_list = URL_MATCHER.findall(content)
            for link in link_list:
                url = urlparse(link)
                domain = url.hostname
                if (domain in domain_list) is not domains_allowed:
                    await self.censor_message(message_id, content, channel, member, url.hostname, "_domain_blocked")
                    return

        if censor_emoji_message and content is not None and len(content) > 0:
            new_content = ''.join(c for c in content if c not in emoji.UNICODE_EMOJI)
            new_content = re.sub(EMOJI_REGEX, '', new_content)
            if new_content == '':
                await self.censor_message(message_id, content, channel, member, '', "_emoji_only")
                return




    async def censor_message(self, message_id, content, channel, member, bad, key=""):
        if channel.permissions_for(channel.guild.me).manage_messages:
            try:
                self.bot.data["message_deletes"].add(message_id)
                await channel.delete_messages([discord.Object(message_id)])
            except discord.NotFound as ex:
                pass
            else:
                clean_message = await Utils.clean(content, channel.guild, markdown=False)
                GearbotLogging.log_key(channel.guild.id, f'censored_message{key}', user=member, user_id=member.id,
                                       message=clean_message, sequence=bad, channel=channel.mention)
        else:

            clean_message = await Utils.clean(content, channel.guild, markdown=False)
            GearbotLogging.log_key(channel.guild.id, f'censored_message_failed{key}', user=member,
                                   user_id=member.id, message=clean_message, sequence=bad,
                                   link='https://discord.com/channels/{0}/{1}/{2}'.format(channel.guild.id, channel.id, message_id))

    async def censor_invite(self, member, message_id, channel, code, server_name, content):
        # Allow for users with a trusted role, or trusted users, to post invite links
        if Configuration.get_var(member.guild.id, "CENSORING", "ALLOW_TRUSTED_BYPASS") and Permissioncheckers.is_trusted(
                member):
            return

        self.bot.data["message_deletes"].add(message_id)
        clean_message = await Utils.clean(content, member.guild)
        clean_name = Utils.clean_user(member)
        try:
            await channel.delete_messages([discord.Object(message_id)])
            GearbotLogging.log_key(member.guild.id, 'censored_invite', user=clean_name, code=code, message=clean_message,
                                   server_name=server_name, user_id=member.id,
                                   channel=channel.mention)
        except discord.NotFound:
            # we failed? guess we lost the race, log anyways
            GearbotLogging.log_key(member.guild.id, 'invite_censor_fail', user=clean_name, code=code,
                                   message=clean_message, server_name=server_name, user_id=member.id,
                                   channel=channel.mention)
            if message_id in self.bot.data["message_deletes"]:
                self.bot.data["message_deletes"].remove(message_id)
        except discord.Forbidden:
            GearbotLogging.log_key(member.guild.id, 'invite_censor_forbidden', user=clean_name, code=code,
                                   message=clean_message, server_name=server_name, user_id=member.id,
                                   channel=channel.mention)
            if message_id in self.bot.data["message_deletes"]:
                self.bot.data["message_deletes"].remove(message_id)


def setup(bot):
    bot.add_cog(Censor(bot))
