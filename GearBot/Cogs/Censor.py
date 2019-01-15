import discord
from discord.ext.commands import clean_content

from Bot.GearBot import GearBot
from Util import Configuration, GearbotLogging, Permissioncheckers, Translator, Utils, InfractionUtils, Emoji
from Util.Matchers import INVITE_MATCHER
from database.DatabaseConnector import Infraction


async def censor_invite(ctx, code, server_name):
    ctx.bot.data["message_deletes"].add(ctx.message.id)
    clean_message = await clean_content().convert(ctx, ctx.message.content)
    clean_name = Utils.clean_user(ctx.message.author)
    try:
        await ctx.message.delete()
        GearbotLogging.log_to(ctx.guild.id, "CENSORED_MESSAGES",
                              f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('censored_invite', ctx.guild.id, user=clean_name, code=code, message=clean_message, server_name=server_name, user_id=ctx.message.author.id, channel=ctx.message.channel.mention)}")
    except discord.NotFound:
        if ctx.message.id in ctx.bot.data["message_deletes"]:
            ctx.bot.data["message_deletes"].remove(ctx.message.id)
        # we failed? guess we lost the race, log anyways
        GearbotLogging.log_to(ctx.guild.id, "CENSORED_MESSAGES",
                              f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('invite_censor_fail', ctx.guild.id, user=clean_name, code = code, message = clean_message, server_name = server_name, user_id = ctx.message.author.id, channel = ctx.message.channel.mention)}")


class Censor:

    def __init__(self, bot):
        self.bot: GearBot = bot

    async def on_message(self, message: discord.Message):
        await self.censor_message(message)

    async def on_raw_message_edit(self, event: discord.RawMessageUpdateEvent):
        channel = self.bot.get_channel(int(event.data["channel_id"]))
        if channel is not None:
            permissions = channel.permissions_for(channel.guild.me)
            if permissions.read_messages and permissions.read_message_history:
                try:
                    message = await channel.get_message(event.message_id)
                except discord.NotFound:
                    pass
                else:
                    await self.censor_message(message)

    async def censor_message(self, message: discord.Message):
        ctx = await self.bot.get_context(message)
        if message.guild is None or \
                message.webhook_id is not None or \
                message.author == message.guild.me or \
                not Configuration.get_var(message.guild.id, "CENSOR_MESSAGES") or \
                Permissioncheckers.get_user_lvl(ctx) >= 2:
            return

        blacklist = Configuration.get_var(message.guild.id, "WORD_BLACKLIST")
        max_mentions = Configuration.get_var(message.guild.id, "MAX_MENTIONS")
        guilds = Configuration.get_var(message.guild.id, "INVITE_WHITELIST")
        content = message.content.replace('\\', '')
        censored = False
        if len(guilds) is not 0:
            codes = INVITE_MATCHER.findall(content)
            for code in codes:
                try:
                    invite: discord.Invite = await self.bot.get_invite(code)
                except discord.NotFound:
                    await censor_invite(ctx, code, "INVALID INVITE")
                except KeyError:
                    await censor_invite(ctx, code, "DM group")
                    censored = True
                else:
                    if invite.guild is None or (not invite.guild.id in guilds and invite.guild.id != message.guild.id):
                        await censor_invite(ctx, code, invite.guild.name)
                        censored = True

        if not censored:
            content = content.lower()
            for bad in (w.lower() for w in blacklist):
                if bad in content:
                    if message.channel.permissions_for(message.guild.me).manage_messages:
                        try:
                            self.bot.data["message_deletes"].add(message.id)
                            await message.delete()
                        except discord.NotFound as ex:
                            pass  # lost the race with another bot?
                        else:
                            clean_message = await clean_content().convert(ctx, message.content)
                            GearbotLogging.log_to(ctx.guild.id, "CENSORED_MESSAGES",
                                                  f":no_entry_sign: {Translator.translate('censored_message', ctx.guild.id, user=message.author, user_id=message.author.id, message=clean_message, sequence=bad, channel=message.channel.mention)}")
                    else:
                        clean_message = await clean_content().convert(ctx, message.content)
                        GearbotLogging.log_to(ctx.guild.id, "CENSORED_MESSAGES",
                                              f":no_entry_sign: {Translator.translate('censor_message_failed', ctx.guild.id, user=message.author, user_id=message.author.id, message=clean_message, sequence=bad, link=message.jump_url)}")

        mentions = len(message.mentions) + len(message.role_mentions)
        if mentions > max_mentions > 4:
            self.bot.data["forced_exits"].add(message.author.id)
            reason = Translator.translate('autoban_too_many_mentions', message.guild.id, count=mentions)

            if message.guild.me.guild_permissions.ban_members:
                await message.guild.ban(message.author, reason=reason)
                Infraction.update(active=False).where(
                    (Infraction.user_id == message.author.id) & (Infraction.type == "Unban") &
                    (Infraction.guild_id == ctx.guild.id)).execute()
                InfractionUtils.add_infraction(message.guild.id, message.author.id, self.bot.user.id, "AUTOBAN", reason)
                GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                                      f":door: {Translator.translate('ban_log', ctx.guild.id, user=message.author, user_id=message.author.id, moderator=self.bot.user, moderator_id=self.bot.user.id, reason=reason)}")
            else:
                self.bot.data["forced_exits"].remove(message.author.id)
                translated = Translator.translate('automod_ban_failed', message.guild.id, user=message.author,
                                                  user_id=message.author.id, reason=reason)
                GearbotLogging.log_to(message.guild.id, "MOD_ACTIONS",
                                      f"{Emoji.get_chat_emoji('WARNING')} {translated}")


def setup(bot):
    bot.add_cog(Censor(bot))
