import asyncio
import re

import discord
from discord.ext import commands
from discord.ext.commands import clean_content

from Util import Configuration, GearbotLogging, Permissioncheckers

INVITE_MATCHER = re.compile(r"(?:https?:\/\/)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discordapp\.com\/invite)\/([\w|\d|-]+)")
class Censor:

    def __init__(self, bot):
        self.bot: commands.Bot = bot

    async def on_message(self, message: discord.Message):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        if not hasattr(message.channel, "guild") or message.channel.guild is None:
            return
        ctx: commands.Context = await self.bot.get_context(message)
        guild = message.guild
        is_mod = Permissioncheckers.isServerMod(ctx)
        if message.author == guild.me or is_mod or message.author.id in Configuration.getConfigVar(guild.id, "IGNORED_USERS"):
            return
        guilds = Configuration.getConfigVar(message.guild.id, "INVITE_WHITELIST")
        if len(guilds) is not 0:
            codes = re.findall(INVITE_MATCHER, message.content)
            for code in codes:
                try:
                    invite:discord.Invite = await self.bot.get_invite(code)
                except discord.NotFound:
                    pass
                else:
                    if not invite.guild.id in guilds and invite.guild.id != guild.id:
                        await message.delete()
                        clean_message = await clean_content().convert(ctx ,message.content)
                        await GearbotLogging.log_to_minor_log(message.guild, f":no_entry_sign: Censored message by {message.author.name}#{message.author.discriminator}, invite code `{code}` to `{invite.guild.name}` is not allowed\n```{clean_message}```")

def setup(bot):
    bot.add_cog(Censor(bot))