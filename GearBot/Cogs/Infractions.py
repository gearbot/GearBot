import re
import typing

import discord
from discord.ext import commands
from discord.ext.commands import BadArgument

from Cogs.BaseCog import BaseCog
from Util import InfractionUtils, Emoji, Utils, GearbotLogging, Translator, Configuration, \
    Confirmation, MessageUtils, ReactionManager
from Util.Converters import UserID, Reason, InfSearchLocation, ServerInfraction


class Infractions(BaseCog):

    def __init__(self, bot):
        super().__init__(bot, {
            "min": 2,
            "max": 6,
            "required": 2,
            "commands": {
                "inf": {
                    "required": 2,
                    "min": 2,
                    "max": 6,
                    "commands": {
                        "delete": {"required": 5, "min": 3, "max": 6}
                    }
                }
            }
        })

    @commands.guild_only()
    @commands.command()
    async def warn(self, ctx:commands.Context, member:discord.Member, *, reason:Reason):
        """warn_help"""
        if ctx.author != member and (ctx.author.top_role > member.top_role or ctx.guild.owner == ctx.author):
            if member.id == self.bot.user.id:
                async def yes():
                    channel = self.bot.get_channel(Configuration.get_master_var("inbox", 0))
                    if channel is not None:
                        await channel.send(f"[`{ctx.message.created_at.strftime('%c')}`] {ctx.message.author} (`{ctx.message.author.id}`) submitted feedback: {reason}")
                        await MessageUtils.send_to(ctx, 'YES', 'feedback_submitted')
                message = MessageUtils.assemble(ctx, "THINK", "warn_to_feedback")
                await Confirmation.confirm(ctx, message, on_yes=yes)
            else:
                i = InfractionUtils.add_infraction(ctx.guild.id, member.id, ctx.author.id, "Warn", reason)
                name = Utils.clean_user(member)
                await MessageUtils.send_to(ctx, 'YES', 'warning_added', user=name, inf=i.id)
                aname = Utils.clean_user(ctx.author)
                GearbotLogging.log_to(ctx.guild.id, 'warning_added_modlog', user=name, moderator=aname, reason=reason, user_id=member.id, moderator_id=ctx.author.id, inf=i.id)
                if Configuration.get_var(ctx.guild.id, "DM_ON_WARN"):
                    try:
                        dm_channel = await member.create_dm()
                        await dm_channel.send(f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('warning_dm', ctx.guild.id, server=ctx.guild.name)}```{reason}```")
                    except discord.Forbidden:
                        GearbotLogging.log_to(ctx.guild.id, 'warning_could_not_dm', ctx.guild.id, user=name, userid=member.id)
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
                        try:
                            query = await UserID().convert(ctx, parts[0])
                        except BadArgument:
                            query = parts[0]

                else:
                    query = (" ".join(parts[:-1])).strip()
            except ValueError:
                amount = 100
            else:
                if 1 < amount > 500:
                    if query == "":
                        query = amount
                    else:
                        query = f"{query} {amount}"
                    amount = 100
        else:
            amount = 100
        # inform user we are working on it
        message = await MessageUtils.send_to(ctx, 'SEARCH', 'inf_search_compiling')
        parts = await InfractionUtils.inf_update(message, query, fields, amount, 0)
        await ReactionManager.register(self.bot, message.id, message.channel.id, "inf_search", **parts)
        pipe = self.bot.redis_pool.pipeline()
        pipe.sadd(f"inf_track:{ctx.guild.id}", message.id)
        pipe.expire(f"inf_track:{ctx.guild.id}", 60*60*24)
        await pipe.execute()
        self.bot.loop.create_task(InfractionUtils.inf_cleaner(ctx.guild.id))



    @inf.command()
    async def update(self, ctx:commands.Context, infraction:ServerInfraction, *, reason:Reason):
        """inf_update_help"""
        infraction.mod_id = ctx.author.id
        infraction.reason = reason
        infraction.save()
        await MessageUtils.send_to(ctx, 'YES', 'inf_updated', id=infraction.id)
        await InfractionUtils.clear_cache(ctx.guild.id)

    @inf.command(aliases=["del", "remove"])
    async def delete(self, ctx:commands.Context, infraction:ServerInfraction):
        """inf_delete_help"""
        reason = infraction.reason
        target = await Utils.get_user(infraction.user_id)
        mod = await Utils.get_user(infraction.mod_id)
        async def yes():
            infraction.delete_instance()
            await MessageUtils.send_to(ctx, "YES", "inf_delete_deleted", id=infraction.id)
            GearbotLogging.log_to(ctx.guild.id, 'inf_delete_log', id=infraction.id, target=Utils.clean_user(target), target_id=target.id, mod=Utils.clean_user(mod), mod_id=mod.id, reason=reason, user=Utils.clean_user(ctx.author), user_id=ctx.author.id)
            await InfractionUtils.clear_cache(ctx.guild.id)
        await Confirmation.confirm(ctx, text=f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('inf_delete_confirmation', ctx.guild.id, id=infraction.id, user=Utils.clean_user(target), user_id=target.id, reason=reason)}", on_yes=yes)

    @inf.command('claim')
    async def claim(self, ctx, infraction:ServerInfraction):
        """inf_claim_help"""
        infraction.mod_id = ctx.author.id
        infraction.save()
        await MessageUtils.send_to(ctx, 'YES', 'inf_claimed', inf_id=infraction.id)
        await InfractionUtils.clear_cache(ctx.guild.id)

    IMAGE_MATCHER = re.compile(r'((?:https?://)[a-z0-9]+(?:[-.][a-z0-9]+)*\.[a-z]{2,5}(?::[0-9]{1,5})?(?:/[^ \n<>]*)\.(?:png|apng|jpg|gif))',re.IGNORECASE)

    @inf.command("info", aliases=["details"])
    async def info(self, ctx, infraction:ServerInfraction):
        """inf_info_help"""
        embed = discord.Embed(color=0x00cea2, description=f"**{Translator.translate('reason', ctx)}**\n{infraction.reason}", timestamp=infraction.start)
        user = await Utils.get_user(infraction.user_id)
        mod = await Utils.get_user(infraction.mod_id)
        key = f"inf_{infraction.type.lower().replace(' ', '_')}"
        if infraction.end is None:
            duration = Translator.translate("unknown_duration", ctx)
        else:
            time = (infraction.end - infraction.start).total_seconds()
            if time % (60 * 60 * 24 * 7) == 0:
                duration = Translator.translate('weeks', ctx, weeks=int(time / (60 * 60 * 24 * 7)))
            elif time % (60 * 60 * 24) == 0:
                duration = Translator.translate('days', ctx, days=int(time / (60 * 60 * 24)))
            elif time % (60 * 60) == 0:
                duration = Translator.translate('hours_solo', ctx, hours=int(time / (60 * 60)))
            elif time % 60 == 0:
                duration = Translator.translate('minutes', ctx, minutes=int(time / 60))
            else:  # if you wana mute for someone for an arbitrary amount of seconds that isn't round minute, hour, day or week then it's not my problem it shows arbitrary amount of seconds
                duration = Translator.translate('seconds', ctx, seconds=int(time))
        embed.set_author(name=Translator.translate(key, ctx, mod=Utils.username_from_user(mod), user=Utils.username_from_user(user), duration=duration),
                         icon_url=mod.avatar_url)
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name=Translator.translate('moderator', ctx), value=Utils.clean_user(mod))
        embed.add_field(name=Translator.translate('user', ctx), value=Utils.clean_user(user))
        embed.add_field(name=Translator.translate('mod_id', ctx), value=infraction.mod_id)
        embed.add_field(name=Translator.translate('user_id', ctx), value=infraction.user_id)
        embed.add_field(name=Translator.translate('inf_added', ctx), value=infraction.start)
        if infraction.end is not None:
            embed.add_field(name=Translator.translate('inf_end', ctx), value=infraction.end)
        embed.add_field(name=Translator.translate('inf_active', ctx), value=MessageUtils.assemble(ctx, 'YES' if infraction.active else 'NO', str(infraction.active).lower()))
        images = self.IMAGE_MATCHER.findall(infraction.reason)
        if len(images) > 0:
            embed.set_image(url=images[0])
        await ctx.send(embed=embed)



def setup(bot):
    bot.add_cog(Infractions(bot))
