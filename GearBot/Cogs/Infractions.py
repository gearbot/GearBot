import typing

import discord
from discord.ext import commands

from Bot.GearBot import GearBot
from Util import Permissioncheckers, InfractionUtils, Emoji, Utils, Pages, GearbotLogging, Translator, Configuration, \
    Confirmation, MessageUtils
from Util.Converters import UserID, Reason, InfSearchLocation
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
                    "delete": {"required": 5, "min": 4, "max": 6}
                }
            }
        }
    }

    def __init__(self, bot):
        self.bot: GearBot = bot
        Pages.register("inf_search", self.inf_init, self.update_infs)

    def __unload(self):
        Pages.unregister("inf_search")

    async def __local_check(self, ctx):
        return Permissioncheckers.check_permission(ctx)

    @commands.guild_only()
    @commands.command()
    async def warn(self, ctx:commands.Context, member:discord.Member, *, reason:Reason):
        """warn_help"""
        if (ctx.author != member  and ctx.author.top_role > member.top_role) or ctx.guild.owner == ctx.author:
            if len(reason) > 1800:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('warning_to_long', ctx.guild.id)}")
            else:
                if member.id == self.bot.user.id:
                    async def yes():
                        channel = self.bot.get_channel(Configuration.get_master_var("inbox", 0))
                        if channel is not None:
                            await channel.send(f"[`{ctx.message.created_at.strftime('%c')}`] {ctx.message.author} (`{ctx.message.author.id}`) submitted feedback: {reason}")
                            await MessageUtils.send_to(ctx, 'YES', 'feedback_submitted')
                    message = MessageUtils.assemble(ctx, "THINK", "warn_to_feedback")
                    await Confirmation.confirm(ctx, message, on_yes=yes)
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
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('warning_not_allowed', ctx.guild.id, user=member)}")

    @commands.guild_only()
    @commands.group(aliases=["infraction", "infractions"])
    async def inf(self, ctx:commands.Context):
        """inf_help"""
        pass

    @inf.command()
    async def search(self, ctx:commands.Context, fields:commands.Greedy[InfSearchLocation]=None, *, query:typing.Union[UserID, str]=""):
        """inf_search_help"""
        if fields is None or len(fields) is 0:
            fields = ["[user]", "[mod]", "[reason]"]
        if isinstance(query, str):
            parts = query.split(" ")
            try:
                amount = int(parts[-1])
                if len(parts) is 2:
                    try:
                        query = int(parts[0])
                    except ValueError:
                        query = parts[0]
                else:
                    query = " ".join(parts[:-1])
            except ValueError:
                amount = 25
            else:
                if 1 < amount > 50:
                    query += f" {amount}"
                    amount = 25
        else:
            amount=25
        await Pages.create_new("inf_search", ctx, guild_id=ctx.guild.id, query=query, amount=amount, fields=fields)

    async def inf_init(self, ctx:commands.Context, query, guild_id, amount, fields):
        pages = await InfractionUtils.get_infraction_pages(guild_id, query, amount, fields)
        name = await Utils.username(query) if isinstance(query, int) else ctx.guild.name
        return f"{MessageUtils.assemble(ctx, 'SEARCH', 'inf_search_header', name=name, page_num=1, pages=len(pages))}{pages[0]}", None, len(pages) > 1, []

    async def update_infs(self, ctx, message, page_num, action, data):
        pages = await InfractionUtils.get_infraction_pages(data["guild_id"], data["query"], data["amount"] if "amount" in data else 25, data["fields"] if "fields" in data else ["user", "mod", "reason"])
        page, page_num = Pages.basic_pages(pages, page_num, action)
        name = await Utils.username(data['query']) if isinstance(data['query'], int) else self.bot.get_guild(data["guild_id"]).name
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
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('inf_updated', ctx.guild.id, id=inf_id)}")
            await InfractionUtils.clear_cache(ctx.guild.id)

    @inf.command(aliases=["del", "remove"])
    async def delete(self, ctx:commands.Context, inf_id:int):
        """inf_delete_help"""
        infraction = Infraction.get_or_none(id=inf_id, guild_id=ctx.guild.id)
        if infraction is None:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('inf_not_found', ctx.guild.id, id=inf_id)}")
        else:
            reason = infraction.reason
            target = await Utils.get_user(infraction.user_id)
            mod = await Utils.get_user(infraction.mod_id)
            async def yes():
                infraction.delete_instance()
                await MessageUtils.send_to(ctx, "YES", "inf_delete_deleted", id=inf_id)
                GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                    f":wastebasket: {Translator.translate('inf_delete_log', ctx.guild.id, id=inf_id, target=str(target), target_id=target.id, mod=str(mod), mod_id=mod.id, reason=reason, user=str(ctx.author), user_id=ctx.author.id)}")
                await InfractionUtils.clear_cache(ctx.guild.id)
            await Confirmation.confirm(ctx, text=f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('inf_delete_confirmation', ctx.guild.id, id=inf_id, user=str(target), user_id=target.id, reason=reason)}", on_yes=yes)

def setup(bot):
    bot.add_cog(Infractions(bot))
