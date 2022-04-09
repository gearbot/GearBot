import asyncio
import json
import re
import datetime

import disnake
from disnake import Interaction
from disnake.ext import commands
from disnake.ext.commands import BadArgument, Greedy, BucketType

from Cogs.BaseCog import BaseCog
from Util import InfractionUtils, Emoji, Utils, GearbotLogging, Translator, Configuration, \
    MessageUtils, Pages, Actions
from Util.Converters import UserID, Reason, InfSearchLocation, ServerInfraction, PotentialID, DiscordUser, \
    TranslatedBadArgument
from Util.InfractionUtils import get_key
from views import SimplePager
from views.Confirm import Confirm
from views.InfSearch import InfSearch


class Infractions(BaseCog):

    async def _warn(self, ctx, target, *, reason, message=True, dm_action=True):
        i = await InfractionUtils.add_infraction(ctx.guild.id, target.id, ctx.author.id, "Warn", reason)
        name = Utils.clean_user(target)
        if message:
            await MessageUtils.send_to(ctx, 'YES', 'warning_added', user=name, inf=i.id)
        aname = Utils.clean_user(ctx.author)
        GearbotLogging.log_key(ctx.guild.id, 'warning_added_modlog', user=name, moderator=aname, reason=reason,
                               user_id=target.id, moderator_id=ctx.author.id, inf=i.id)
        if Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_WARN") and dm_action:
            await Utils.send_infraction(self.bot, target, ctx.guild, 'WARNING', 'warn', reason)

    @commands.guild_only()
    @commands.command()
    async def warn(self, ctx: commands.Context, member: DiscordUser, *, reason: Reason):
        """warn_help"""
        # don't allow warning GearBot, get some feedback about issues instead

        Utils.enrich_reason(ctx, reason)
        if len(reason) > 1800:
            raise TranslatedBadArgument('reason_too_long', ctx)

        if hasattr(member, 'system') and hasattr(member, 'system') and member.system:
            await MessageUtils.send_to(ctx, 'NO', 'cant_warn_system_user')
            return

        if member.bot:
            await MessageUtils.send_to(ctx, "THINK", "cant_warn_bot")
            return

        await Actions.act(ctx, "warning", member.id, self._warn, allow_bots=False, reason=reason,
                          check_bot_ability=False, require_on_server=False)

    @commands.guild_only()
    @commands.command()
    async def note(self, ctx, member: DiscordUser, *, reason: Reason):
        i = await InfractionUtils.add_infraction(ctx.guild.id, member.id, ctx.author.id, "Note", reason)
        name = Utils.clean_user(member)
        await MessageUtils.send_to(ctx, 'YES', 'note_added', user=name, inf=i.id)
        aname = Utils.clean_user(ctx.author)
        GearbotLogging.log_key(ctx.guild.id, 'note_added_modlog', user=name, moderator=aname, reason=reason,
                               user_id=member.id, moderator_id=ctx.author.id, inf=i.id)

    @commands.guild_only()
    @commands.command()
    async def mwarn(self, ctx, targets: Greedy[PotentialID], *, reason: Reason):
        """mwarn_help"""

        reason += ",".join(
            Utils.assemble_attachment(ctx.message.channel.id, attachment.id, attachment.filename) for attachment in
            ctx.message.attachments)
        if len(reason) > 1800:
            raise TranslatedBadArgument('reason_too_long', ctx)

        message = None
        async def yes(interaction: Interaction):
            await interaction.response.edit_message(content=MessageUtils.assemble(ctx, "REFRESH", "processing"), view=None)
            failures = await Actions.mass_action(ctx, "warning", targets, self._warn, max_targets=10, allow_bots=False,
                                                 message=False, reason=reason, dm_action=True)

            await interaction.edit_original_message(content=MessageUtils.assemble(ctx, "YES", "mwarn_confirmation", count=len(targets) - len(failures)))
            if len(failures) > 0:
                f = "\n".join(failures)
                pipe = self.bot.redis_pool.pipeline()
                k = f'mass_failures:{ctx.message.id}'
                pipe.set(k, f)
                pipe.expire(k, 7 * 24 * 60 * 60)
                await pipe.execute()
                pages = Pages.paginate(f, prefix='```\n', suffix='```')
                content, view, _ = SimplePager.get_parts(pages, 0,  ctx.guild.id, f'mass_failures:{ctx.message.id}:warn')
                await ctx.send(f"**{Translator.translate('mass_failures_warn', ctx, page_num=1, pages=len(pages))}**{content}", view=view)


        async def no(interaction):
            await interaction.response.edit_message(
                content=MessageUtils.assemble(ctx, 'NO', 'command_canceled'), view=None)

        async def timeout():
            if message is not None:
                await message.edit(content=MessageUtils.assemble(ctx, 'NO', 'command_canceled'), view=None)

        def check(interaction: Interaction):
            return ctx.author.id == interaction.user.id and interaction.message.id == message.id

        if len(targets) > 10:
            await MessageUtils.send_to(ctx, "NO", "mass_action_too_many_people", max=10)
            return
        if len(targets) > 0:
            message = await ctx.send(Translator.translate("mwarn_confirm", ctx), view=
                           Confirm(ctx.guild.id, on_yes=yes, on_no=no, on_timeout=timeout, check=check))
        else:
            await Utils.empty_list(ctx, "warn")

    @commands.guild_only()
    @commands.group(aliases=["infraction", "infractions"], invoke_without_command=True)
    async def inf(self, ctx: commands.Context):
        """inf_help"""
        pass

    @inf.command()
    async def search(self, ctx: commands.Context, fields: commands.Greedy[InfSearchLocation] = None, *,
                     query: str = ""):
        """inf_search_help"""
        if fields is None or len(fields) == 0:
            fields = ["[user]", "[mod]", "[reason]"]
        if isinstance(query, str):
            parts = query.split(" ")
            try:
                amount = int(parts[-1])
                if len(parts) == 2:
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
                if parts[0] != "":
                    try:
                        query = await UserID().convert(ctx, parts[0])
                    except BadArgument:
                        query = parts[0]
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
        search_meta = {
            "amount": amount,
            "query": query,
            "fields": ' '.join(fields),
            "current_page": 0,
        }

        pipe = self.bot.redis_pool.pipeline()

        message = await MessageUtils.send_to(ctx, 'SEARCH', 'inf_search_compiling')
        pipe.set(f"inf_meta:{message.id}", json.dumps(search_meta))
        pipe.expire(f"inf_meta:{message.id}", 60 * 60 * 24)
        pipe.sadd(f"inf_track:{ctx.guild.id}", message.id)
        pipe.expire(f"inf_track:{ctx.guild.id}", 60 * 60 * 24)
        await pipe.execute()

        pages = await InfractionUtils.fetch_infraction_pages(ctx.guild.id, query, amount, fields, 0)
        page = await self.bot.wait_for('page_assembled', check=lambda l: l['key'] == get_key(ctx.guild.id, query, fields, amount) and l['page_num'] == 0)
        await message.edit(
            content=await InfractionUtils.assemble_message(ctx.guild.id, page['page'], query, 0, pages),
                                                     view=InfSearch(filters=fields, pages=pages, guild_id=ctx.guild.id)
        )



    @inf.command()
    async def update(self, ctx: commands.Context, infraction: ServerInfraction, *, reason: Reason):
        """inf_update_help"""
        reason += ",".join(
            Utils.assemble_attachment(ctx.message.channel.id, attachment.id, attachment.filename) for attachment in
            ctx.message.attachments)
        if len(reason) > 1800:
            raise TranslatedBadArgument('reason_too_long', ctx)

        infraction.mod_id = ctx.author.id
        infraction.reason = reason
        await infraction.save()
        await MessageUtils.send_to(ctx, 'YES', 'inf_updated', id=infraction.id)
        InfractionUtils.clear_cache(ctx.guild.id)
        user = await Utils.get_user(infraction.user_id)
        GearbotLogging.log_key(ctx.guild.id, "inf_update_log", inf=infraction.id, user=Utils.clean_user(user),
                               userid=user.id, mod=Utils.clean_user(ctx.author), modid=ctx.author.id, reason=reason)

    @inf.command(aliases=["del", "remove", "clear"])
    async def delete(self, ctx: commands.Context, infraction: ServerInfraction):
        """inf_delete_help"""
        reason = infraction.reason
        target = await Utils.get_user(infraction.user_id)
        mod = await Utils.get_user(infraction.mod_id)

        async def yes(interaction: disnake.Interaction):
            await infraction.delete()
            await interaction.response.edit_message(
                content=MessageUtils.assemble(ctx, "YES", "inf_delete_deleted", id=infraction.id), view=None)
            GearbotLogging.log_key(ctx.guild.id, 'inf_delete_log', id=infraction.id, target=Utils.clean_user(target),
                                   target_id=target.id, mod=Utils.clean_user(mod),
                                   mod_id=mod.id if mod is not None else 0, reason=reason,
                                   user=Utils.clean_user(ctx.author), user_id=ctx.author.id)
            InfractionUtils.clear_cache(ctx.guild.id)

        async def no(interaction):
            await interaction.response.edit_message(
                content=MessageUtils.assemble(ctx, 'NO', 'command_canceled'), view=None
            )

        async def timeout():
            if message is not None:
                await message.edit(content=MessageUtils.assemble(ctx, 'NO', 'command_canceled'), view=None)

        def check(interaction):
            return ctx.author.id == interaction.user.id and interaction.message.id == message.id

        message = await ctx.send(
            f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('inf_delete_confirmation', ctx.guild.id, id=infraction.id, user=Utils.clean_user(target), user_id=target.id, reason=reason)}",
            view=Confirm(ctx.guild.id, on_yes=yes, on_no=no, on_timeout=timeout, check=check))

    @inf.command('claim')
    async def claim(self, ctx, infraction: ServerInfraction):
        """inf_claim_help"""
        infraction.mod_id = ctx.author.id
        await infraction.save()
        await MessageUtils.send_to(ctx, 'YES', 'inf_claimed', inf_id=infraction.id)
        InfractionUtils.clear_cache(ctx.guild.id)

    IMAGE_MATCHER = re.compile(
        r'((?:https?://)[a-z0-9]+(?:[-.][a-z0-9]+)*\.[a-z]{2,5}(?::[0-9]{1,5})?(?:/[^ \n<>]*)\.(?:png|apng|jpg|gif))',
        re.IGNORECASE)

    @inf.command("info", aliases=["details"])
    @commands.bot_has_permissions(embed_links=True)
    async def info(self, ctx, infraction: ServerInfraction):
        """inf_info_help"""
        embed = disnake.Embed(color=0x00cea2,
                              description=f"**{Translator.translate('reason', ctx)}**\n{infraction.reason}",
                              timestamp=datetime.datetime.utcfromtimestamp(infraction.start).replace(
                                  tzinfo=datetime.timezone.utc))
        user = await Utils.get_user(infraction.user_id)
        mod = await Utils.get_user(infraction.mod_id)
        key = f"inf_{infraction.type.lower().replace(' ', '_')}"
        if infraction.end is None:
            duration = Translator.translate("unknown_duration", ctx)
        else:
            time = (datetime.datetime.utcfromtimestamp(infraction.end) - datetime.datetime.utcfromtimestamp(
                infraction.start)).total_seconds()
            duration = Utils.to_pretty_time(time, ctx.guild.id)

        embed.set_author(
            name=Translator.translate(key, ctx, mod=Utils.username_from_user(mod), user=Utils.username_from_user(user),
                                      duration=duration),
            icon_url=mod.avatar.url)
        embed.set_thumbnail(url=user.avatar.url)
        embed.add_field(name=Translator.translate('moderator', ctx), value=Utils.clean_user(mod))
        embed.add_field(name=Translator.translate('user', ctx), value=Utils.clean_user(user))
        embed.add_field(name=Translator.translate('mod_id', ctx), value=infraction.mod_id)
        embed.add_field(name=Translator.translate('user_id', ctx), value=infraction.user_id)
        embed.add_field(name=Translator.translate('inf_added', ctx),
                        value=datetime.datetime.utcfromtimestamp(infraction.start).replace(
                            tzinfo=datetime.timezone.utc))
        if infraction.end is not None:
            embed.add_field(name=Translator.translate('inf_end', ctx),
                            value=datetime.datetime.utcfromtimestamp(infraction.end).replace(
                                tzinfo=datetime.timezone.utc))
        embed.add_field(name=Translator.translate('inf_active', ctx),
                        value=MessageUtils.assemble(ctx, 'YES' if infraction.active else 'NO',
                                                    str(infraction.active).lower()))
        images = self.IMAGE_MATCHER.findall(infraction.reason)
        if len(images) > 0:
            embed.set_image(url=images[0])
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Infractions(bot))
