import discord
from discord.ext import commands

from Util import Permissioncheckers, InfractionUtils, Emoji, Utils, Pages


class Infractions:

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        Pages.register("inf_search", self.inf_init, self.update_infs)

    def __unload(self):
        Pages.unregister("inf_search")

    async def __local_check(self, ctx):
        return Permissioncheckers.isServerMod(ctx)

    @commands.guild_only()
    @commands.command()
    async def warn(self, ctx:commands.Context, member:discord.Member, *, reason:str):
        if (ctx.author != member and member != ctx.bot.user and ctx.author.top_role > member.top_role) or ctx.guild.owner == ctx.author:
            if len(reason) > 1800:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} Warning is to long, I can only store warnings up to 1800 characters.")
            else:
                InfractionUtils.add_infraction(ctx.guild.id, member.id, ctx.author.id, "Warn", reason)
                name = Utils.clean(member.name)
                await ctx.send(f"{Emoji.get_chat_emoji('YES')} warning for {name}#{member.discriminator} added.")
        else:
            name = Utils.clean(member.name)
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} You are not allowed to warn {name}#{member.discriminator}.")

    @commands.guild_only()
    @commands.group()
    async def inf(self, ctx:commands.Context):
        pass

    @inf.command()
    async def search(self, ctx:commands.Context, query:int):
        await Pages.create_new("inf_search", ctx, guild_id=ctx.guild.id, query=query)

    async def inf_init(self, ctx:commands.Context, query, guild_id):
        pages = await InfractionUtils.get_infraction_pages(guild_id, query)
        name = await Utils.username(query)
        return f"**Infractions for {name}** (1/{len(pages)}){pages[0]}", None, len(pages) > 1

    async def update_infs(self, ctx, message, page_num, action, data):
        pages = await InfractionUtils.get_infraction_pages(data["guild_id"], data["query"])
        page, page_num = Pages.basic_pages(pages, page_num, action)
        name = await Utils.username(data['query'])
        return f"**Infractions for {name}** ({page_num+1}/{len(pages)}){page}", None, page_num


def setup(bot):
    bot.add_cog(Infractions(bot))