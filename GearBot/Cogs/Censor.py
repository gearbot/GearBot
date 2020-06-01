import re
from urllib import parse
from urllib.parse import urlparse

import discord
from discord import DMChannel
from discord.ext import commands
from discord.ext.commands import clean_content

from Cogs.BaseCog import BaseCog
from Util import Configuration, GearbotLogging, Permissioncheckers, Utils
from Util.Matchers import INVITE_MATCHER, URL_MATCHER


class Censor(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.regexes = dict()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel is None or isinstance(message.channel, DMChannel) or not Configuration.get_var(message.channel.guild.id, "CENSORING", "ENABLED") or self.bot.user.id == message.author.id:
            return
        await self.check_message(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, event: discord.RawMessageUpdateEvent):
        channel = self.bot.get_channel(int(event.data["channel_id"]))
        if channel is None or isinstance(channel, DMChannel) or not Configuration.get_var(channel.guild.id, "CENSORING", "ENABLED"):
            return
        permissions = channel.permissions_for(channel.guild.me)
        if permissions.read_messages and permissions.read_message_history:
            try:
                message = await channel.fetch_message(event.message_id)
            except (discord.NotFound, discord.Forbidden): # we should never get forbidden, be we do, somehow
                pass
            else:
                if self.bot.user.id != message.author.id:
                    await self.check_message(message)

    async def check_message(self, message: discord.Message):
        if message.guild is None or \
                message.webhook_id is not None or \
                message.author == message.guild.me:
            return
        ctx = await self.bot.get_context(message)
        if Permissioncheckers.get_user_lvl(ctx.guild, ctx.author) >= 2:
            return
        blacklist = Configuration.get_var(message.guild.id, "CENSORING", "TOKEN_BLACKLIST")
        word_blacklist = Configuration.get_var(message.guild.id, "CENSORING", "WORD_BLACKLIST")
        guilds = Configuration.get_var(message.guild.id, "CENSORING", "INVITE_WHITELIST")
        domain_list = Configuration.get_var(message.guild.id, "CENSORING", "DOMAIN_LIST")
        domain_whitelist = Configuration.get_var(message.guild.id, "CENSORING", "DOMAIN_WHITELIST")
        content = message.content.replace('\\', '')
        decoded_content = parse.unquote(content)
        censored = False
        if len(guilds) is not 0:
            codes = INVITE_MATCHER.findall(decoded_content)
            for code in codes:
                try:
                    invite: discord.Invite = await self.bot.fetch_invite(code)
                except discord.NotFound:
                    await self.censor_invite(ctx, code, "INVALID INVITE")
                    return
                if invite.guild is None:
                    await self.censor_invite(ctx, code, "DM group")
                    censored = True
                else:
                    if invite.guild is None or (not invite.guild.id in guilds and invite.guild.id != message.guild.id):
                        await self.censor_invite(ctx, code, invite.guild.name)
                        censored = True

        if not censored:
            content = content.lower()
            for bad in (w.lower() for w in blacklist):
                if bad in content:
                    await self.censor_message(message, bad)
                    censored = True
                    break

        if not censored and len(word_blacklist) > 0:
            if ctx.guild.id not in self.regexes:
                regex = re.compile(r"\b(" + '|'.join(re.escape(word) for word in word_blacklist) + r")\b", re.IGNORECASE)
                self.regexes[ctx.guild.id] = regex
            else:
                regex = self.regexes[ctx.guild.id]
            match = regex.findall(message.content)
            if len(match):
                await self.censor_message(message, match[0], "_word")
                censored = True

        if not censored and len(domain_list) > 0:
            link_list = URL_MATCHER.findall(message.content)
            for link in link_list:
                url = urlparse(link)
                domain = url.hostname
                if (domain in domain_list) is not domain_whitelist:
                    await self.censor_message(message, url.hostname, "_domain_whitelist" if domain_whitelist else "_domain_blacklist")
                print(domain)


    async def censor_message(self, message, bad, key=""):
        if message.channel.permissions_for(message.guild.me).manage_messages:
            try:
                self.bot.data["message_deletes"].add(message.id)
                await message.delete()
            except discord.NotFound as ex:
                pass
            else:
                clean_message = await Utils.clean(message.content, message.guild, markdown=False)
                GearbotLogging.log_key(message.guild.id, f'censored_message{key}', user=message.author, user_id=message.author.id,
                                       message=clean_message, sequence=bad, channel=message.channel.mention)
                self.bot.dispatch("user_censored", message)
        else:

            clean_message = await Utils.clean(message.content, message.guild, markdown=False)
            GearbotLogging.log_key(message.guild.id, f'censor_message_failed{key}', user=message.author,
                                   user_id=message.author.id, message=clean_message, sequence=bad,
                                   link=message.jump_url)
            self.bot.dispatch("user_censored", message)

    async def censor_invite(self, ctx, code, server_name):
        # Allow for users with a trusted role, or trusted users, to post invite links
        if Configuration.get_var(ctx.guild.id, "CENSORING", "ALLOW_TRUSTED_BYPASS") and Permissioncheckers.is_trusted(
                ctx.author):
            return

        ctx.bot.data["message_deletes"].add(ctx.message.id)
        clean_message = await clean_content().convert(ctx, ctx.message.content)
        clean_name = Utils.clean_user(ctx.message.author)
        try:
            await ctx.message.delete()
            GearbotLogging.log_key(ctx.guild.id, 'censored_invite', user=clean_name, code=code, message=clean_message,
                                   server_name=server_name, user_id=ctx.message.author.id,
                                   channel=ctx.message.channel.mention)
        except discord.NotFound:
            # we failed? guess we lost the race, log anyways
            GearbotLogging.log_key(ctx.guild.id, 'invite_censor_fail', user=clean_name, code=code,
                                   message=clean_message, server_name=server_name, user_id=ctx.message.author.id,
                                   channel=ctx.message.channel.mention)
            if ctx.message.id in ctx.bot.data["message_deletes"]:
                ctx.bot.data["message_deletes"].remove(ctx.message.id)
        except discord.Forbidden:
            GearbotLogging.log_key(ctx.guild.id, 'invite_censor_forbidden', user=clean_name, code=code,
                                   message=clean_message, server_name=server_name, user_id=ctx.message.author.id,
                                   channel=ctx.message.channel.mention)
            if ctx.message.id in ctx.bot.data["message_deletes"]:
                ctx.bot.data["message_deletes"].remove(ctx.message.id)
        self.bot.dispatch("user_censored", ctx.message)


def setup(bot):
    bot.add_cog(Censor(bot))
