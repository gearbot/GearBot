import discord
from discord.ext import commands

from Util import Permissioncheckers, InfractionUtils, Emoji, Utils, Pages, GearbotLogging, Translator, Configuration, Confirmation
from Util.Converters import UserID, Reason
from database.DatabaseConnector import Infraction


class Infractions:
    permissions = {
        "min": 2,
        "max": 6,
        "required": 2,
        "commands": {
            "inf" : {
                "required" : 2,
                "commands" : {
                    "delete": {"required": 5, "min": 2, "max": 6}
                }
            }
        }
    }

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        Pages.register("inf_search", self.inf_init, self.update_infs)

    def __unload(self):
        Pages.unregister("inf_search")

    async def __local_check(self, ctx):
        return Permissioncheckers.check_permission(ctx)

    @commands.guild_only()
    @commands.command()
    async def warn(self, ctx:commands.Context, member:discord.Member, *, reason:Reason):
        """warn_help"""
        if (ctx.author != member and member != ctx.bot.user and ctx.author.top_role > member.top_role) or ctx.guild.owner == ctx.author:
            if len(reason) > 1800:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('warning_to_long', ctx.guild.id)}")
            else:
                InfractionUtils.add_infraction(ctx.guild.id, member.id, ctx.author.id, "Warn", reason)
                name = Utils.clean_user(member)
                await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('warning_added', ctx.guild.id, user=name)}")
                aname = Utils.clean_user(ctx.author)
                GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('warning_added_modlog', ctx.guild.id, user=name, moderator=aname, reason=reason)}")
                if Configuration.get_var(ctx.guild.id, "DM_ON_WARN"):
                    try:
                        dm_channel = await member.create_dm()
                        await dm_channel.send(f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('warning_dm', ctx.guild.id, server=ctx.guild.name)}```{reason}```")
                    except discord.Forbidden:
                        GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                                                    f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('warning_could_not_dm', ctx.guild.id, user=name, userid=member.id)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('warning_not_allowed', ctx.guild.id, user=ctx.author)}")

    @commands.guild_only()
    @commands.group()
    async def inf(self, ctx:commands.Context):
        """inf_help"""
        pass

    @inf.command()
    async def search(self, ctx:commands.Context, *, query:UserID=None):
        """inf_search_help"""
        await Pages.create_new("inf_search", ctx, guild_id=ctx.guild.id, query=query)

    async def inf_init(self, ctx:commands.Context, query, guild_id):
        pages = await InfractionUtils.get_infraction_pages(guild_id, query)
        name = await Utils.username(query) if query is not None else  ctx.guild.name
        return f"{Translator.translate('inf_search_header', ctx.guild.id, name=name, page_num=1, pages=len(pages))}{pages[0]}", None, len(pages) > 1, []

    async def update_infs(self, ctx, message, page_num, action, data):
        pages = await InfractionUtils.get_infraction_pages(data["guild_id"], data["query"])
        page, page_num = Pages.basic_pages(pages, page_num, action)
        name = await Utils.username(data['query']) if data['query'] is not None else self.bot.get_guild(data["guild_id"]).name
        return f"{Translator.translate('inf_search_header', ctx.guild.id, name=name, page_num=page_num + 1, pages=len(pages))}{page}", None, page_num


    @inf.command()
    async def update(self, ctx:commands.Context, inf_id:int, *, reason:str):
        """inf_update_help"""
        infraction = Infraction.get_or_none(id=inf_id, guild_id=ctx.guild.id)
        if infraction is None:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('inf_not_found', ctx.guild.id, id=inf_id)}")
        else:
            infraction.mod_id = ctx.author.id
            infraction.reason = reason
            infraction.save()
            if f"{ctx.guild.id}_{infraction.user_id}" in InfractionUtils.cache.keys():
                del InfractionUtils.cache[f"{ctx.guild.id}_{infraction.user_id}"]
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('inf_updated', ctx.guild.id, id=inf_id)}")

    @inf.command()
    async def delete(self, ctx:commands.Context, inf_id:int):
        """inf_delete_help"""
        infraction = Infraction.get_or_none(id=inf_id, guild_id=ctx.guild.id)
        if infraction is None:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('inf_not_found', ctx.guild.id, id=inf_id)}")
        else:
            reason = infraction.reason
            target = self.bot.get_user(infraction.user_id)
            mod = self.bot.get_user(infraction.mod_id)
            async def yes():
                infraction.delete_instance()
                if f"{ctx.guild.id}_{infraction.user_id}" in InfractionUtils.cache.keys():
                    del InfractionUtils.cache[f"{ctx.guild.id}_{infraction.user_id}"]
                await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('inf_delete_deleted', ctx.guild.id, id=inf_id)}")
                GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                    Translator.translate('inf_delete_log', ctx.guild.id, id=inf_id, target=str(target), targetid=target.id, mod=str(mod), modid=mod.id, reason=reason, user=str(ctx.author), userid=ctx.author.id))
            async def no():
                await ctx.send(Translator.translate("inf_delete_cancelled", ctx.guild.id, id=inf_id))
            await Confirmation.confirm(ctx, text=f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('inf_delete_confirmation', ctx.guild.id, id=inf_id)}", on_yes=yes, on_no=no)

def setup(bot):
    bot.add_cog(Infractions(bot))
