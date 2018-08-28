import re

import discord
from discord.ext import commands
from discord.ext.commands import clean_content

from Util import Configuration, GearbotLogging, Permissioncheckers, Translator, Utils

INVITE_MATCHER = re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discordapp\.com\/invite)\/([\w|\d|-]+)", flags=re.IGNORECASE)
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
                    await message.delete()
                    clean_message = await clean_content().convert(ctx, message.content)
                    clean_name = Utils.clean_user(message.author)
                    await GearbotLogging.log_to_minor_log(message.guild,
                                                          f":no_entry_sign: {Translator.translate('censored_invite', ctx.guild.id, user=clean_name, code=code, message=clean_message, server_name='DM group')}")
                else:
                    if invite.guild is None or (not invite.guild.id in guilds and invite.guild.id != guild.id):
                        await message.delete()
                        clean_message = await clean_content().convert(ctx ,message.content)
                        clean_name = Utils.clean_user(message.author)
                        await GearbotLogging.log_to_minor_log(message.guild, f":no_entry_sign: {Translator.translate('censored_invite', ctx.guild.id, user=clean_name, code=code, message=clean_message, server_name=invite.guild.name)}")

def setup(bot):
    bot.add_cog(Censor(bot))