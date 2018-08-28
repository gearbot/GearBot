import re

import discord
from discord.ext import commands
from discord.ext.commands import clean_content

from Util import Configuration, GearbotLogging, Permissioncheckers, Translator, Utils

INVITE_MATCHER = re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discordapp\.com\/invite)\/([\w|\d|-]+)", flags=re.IGNORECASE)


async def censor(ctx, code, server_name):
    try:
        await ctx.message.delete()
        clean_message = await clean_content().convert(ctx, ctx.message.content)
        clean_name = Utils.clean_user(ctx.message.author)
        await GearbotLogging.log_to_minor_log(ctx.message.guild,
                                              f":no_entry_sign: {Translator.translate('censored_invite', ctx.guild.id, user=clean_name, code=code, message=clean_message, server_name=server_name)}")
    except discord.Forbidden:
        pass # we failed? guess we lost the race


class Censor:

    def __init__(self, bot):
        self.bot: commands.Bot = bot

    async def on_message(self, message: discord.Message):
        if not hasattr(message.channel, "guild") or message.channel.guild is None:
            return
        ctx: commands.Context = await self.bot.get_context(message)
        guild = message.guild
        is_mod = Permissioncheckers.get_user_lvl(ctx) >= 2
        if message.author == guild.me or is_mod or message.author.id in Configuration.getConfigVar(guild.id, "IGNORED_USERS"):
            return
        guilds = Configuration.getConfigVar(message.guild.id, "INVITE_WHITELIST")
        if len(guilds) is not 0:
            codes = INVITE_MATCHER.findall(message.content)
            for code in codes:
                try:
                    invite:discord.Invite = await self.bot.get_invite(code)
                except discord.NotFound:
                    pass
                except KeyError:
                    await censor(ctx, code, "DM group")
                else:
                    if invite.guild is None or (not invite.guild.id in guilds and invite.guild.id != guild.id):
                        await censor(ctx, code, invite.guild.name)


def setup(bot):
    bot.add_cog(Censor(bot))