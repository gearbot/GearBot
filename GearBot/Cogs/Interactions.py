import discord
from discord import Interaction, InteractionType, Embed, Forbidden, Member, User
from discord.ext import commands

from Cogs.BaseCog import BaseCog
from Util import Configuration, MessageUtils, Translator, Pages, Emoji, Utils, Permissioncheckers, InfractionUtils
from Util.InfractionUtils import get_key
from views import Help, SimplePager
from views.EphemeralInfSearch import EphemeralInfSearch, get_ephemeral_cached_page
from views.InfSearch import InfSearch
from views.SelfRole import SelfRoleView


class Interactions(BaseCog):
    @commands.Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if interaction.type == InteractionType.component:
            cid = interaction.data.get('custom_id')
            if cid.startswith('self_role'):
                parts = cid.split(':')
                if parts[1] == 'role':
                    rid = parts[2]
                    if rid.isnumeric():
                        rid = int(rid)
                        roles = Configuration.get_var(interaction.guild_id, "ROLES", "SELF_ROLES")
                        if rid in roles:
                            role = interaction.guild.get_role(rid)
                            if role is None:
                                roles.remove(rid)
                                Configuration.set_var(interaction.guild_id, "ROLES", "SELF_ROLES", roles)
                                v = SelfRoleView(guild=interaction.guild, page=0)
                                interaction.response.edit_message(
                                    content=Translator.translate("assignable_roles", interaction.guild_id,
                                                                 server_name=interaction.guild.name, page_num=1,
                                                                 page_count=v.pages), view=v)
                                interaction.followup.send_message(
                                    MessageUtils.assemble(interaction.guild_id, 'WARNING', 'self_role_missing'),
                                    ephemeral=True)
                            else:
                                try:
                                    if role in interaction.user.roles:
                                        await interaction.user.remove_roles(role)
                                        await interaction.response.send_message(
                                            Translator.translate("role_left", interaction.guild_id, role_name=role.name,
                                                                 user=interaction.user), ephemeral=True)
                                    else:
                                        await interaction.user.add_roles(role)
                                        await interaction.response.send_message(
                                            Translator.translate("role_joined", interaction.guild_id,
                                                                 role_name=role.name,
                                                                 user=interaction.user), ephemeral=True)
                                except discord.Forbidden:
                                    await interaction.response.send_message(
                                        f"{Emoji.get_chat_emoji('NO')} {Translator.translate('role_too_high_add', interaction.guild_id, role=role.name)}",
                                        ephemeral=True)
                elif parts[1] == "page":
                    v = SelfRoleView(guild=interaction.guild, page=int(parts[2]))
                    await interaction.response.edit_message(
                        content=Translator.translate("assignable_roles", interaction.guild_id,
                                                     server_name=interaction.guild.name, page_num=int(parts[2]) + 1,
                                                     page_count=v.pages), view=v)
            elif cid.startswith('help:'):
                parts = cid.split(':')
                if parts[1] == 'page':
                    q = parts[3] if parts[3] != 'None' else None
                    content, view = await Help.message_parts(self.bot, q, interaction.guild, interaction.user,
                                                             int(parts[2]))
                    await interaction.response.edit_message(content=content, view=view)
                elif parts[1] == 'selector':
                    q = interaction.data.get('values')[0]
                    q = q if q != 'None' else None
                    content, view = await Help.message_parts(self.bot, q, interaction.guild, interaction.user, 0)
                    await interaction.response.edit_message(content=content, view=view)
            elif cid.startswith('pager:'):
                parts = cid.split(':')
                t = parts[2]
                if t == 'eval':
                    if interaction.user.id not in Configuration.get_master_var('BOT_ADMINS'):
                        return
                    output = await self.bot.redis_pool.get(f'eval:{parts[3]}')
                    if output is None:
                        await interaction.response.send_message("Eval output no longer available", ephemeral=True)
                    else:
                        pages = Pages.paginate(output, prefix='```py\n', suffix='```')
                        content, view, page_num = SimplePager.get_parts(pages, int(parts[1]), interaction.guild_id,
                                                                        f'eval:{parts[3]}')
                        await interaction.response.edit_message(
                            content=f'Eval output {page_num + 1}/{len(pages)}{content}', view=view)
                elif t == 'commands':
                    cog = self.bot.get_command("CustCommands")
                    if cog is not None:
                        pages = cog.get_command_pages(interaction.guild_id)
                        content, view, page_num = SimplePager.get_parts(pages, int(parts[1]), interaction.guild.id,
                                                                        'commands')
                        page = cog.gen_command_page(pages, page_num, interaction.guild)
                        await interaction.response.edit_message(embed=page, view=view)
                elif t == 'emoji':
                    cog = self.bot.get_cog('Emoji')
                    if cog is not None:
                        amount = len(interaction.guild.emojis) + 1
                        content, view, page_num = SimplePager.get_parts(range(amount), int(parts[1]),
                                                                        interaction.guild.id, 'emoji')
                        await interaction.response.edit_message(embed=cog.gen_emoji_page(interaction.guild, page_num),
                                                                view=view)
                elif t == 'role_list':
                    cog = self.bot.get_cog('Moderation')
                    if cog is not None:
                        pages = cog.gen_roles_pages(interaction.guild, parts[3])
                        content, view, page_num = SimplePager.get_parts(pages, int(parts[1]), interaction.guild.id,
                                                                        f'role_list:{parts[3]}')
                        await interaction.response.edit_message(
                            content=f"**{Translator.translate('roles', interaction.guild_id, server_name=interaction.guild.name, page_num=page_num + 1, pages=len(pages))}**```\n{pages[page_num]}```",
                            view=view)
                elif t == 'censor_list':
                    cog = self.bot.get_cog('Moderation')
                    if cog is not None:
                        censor_list = Configuration.get_var(interaction.guild.id, "CENSORING", "TOKEN_CENSORLIST")
                        pages = Pages.paginate("\n".join(censor_list))
                        page, view, page_num = SimplePager.get_parts(pages, int(parts[1]), interaction.guild.id,
                                                                     'censor_list')
                        await interaction.response.edit_message(
                            content=f"**{Translator.translate(f'censor_list', interaction.guild, server=interaction.guild.name, page_num=page_num + 1, pages=len(pages))}**```\n{page}```",
                            view=view)
                elif t == 'word_censor_list':
                    cog = self.bot.get_cog('Moderation')
                    if cog is not None:
                        censor_list = Configuration.get_var(interaction.guild.id, "CENSORING", "WORD_CENSORLIST")
                        pages = Pages.paginate("\n".join(censor_list))
                        page, view, page_num = SimplePager.get_parts(pages, int(parts[1]), interaction.guild.id,
                                                                     'word_censor_list')
                        await interaction.response.edit_message(
                            content=f"**{Translator.translate(f'word_censor_list', interaction.guild, server=interaction.guild.name, page_num=page_num + 1, pages=len(pages))}**```\n{page}```",
                            view=view)
                elif t == 'full_censor_list':
                    cog = self.bot.get_cog('Moderation')
                    if cog is not None:
                        censor_list = Configuration.get_var(interaction.guild.id, "CENSORING", "FULL_MESSAGE_LIST")
                        pages = Pages.paginate("\n".join(censor_list))
                        page, view, page_num = SimplePager.get_parts(pages, int(parts[1]), interaction.guild.id,
                                                                     'full_censor_list')
                        await interaction.response.edit_message(
                            content=f"**{Translator.translate(f'full_censor_list', interaction.guild, server=interaction.guild.name, page_num=page_num + 1, pages=len(pages))}**```\n{page}```",
                            view=view)
                elif t == 'flag_list':
                    cog = self.bot.get_cog('Moderation')
                    if cog is not None:
                        censor_list = Configuration.get_var(interaction.guild.id, "FLAGGING", "TOKEN_LIST")
                        pages = Pages.paginate("\n".join(censor_list))
                        page, view, page_num = SimplePager.get_parts(pages, int(parts[1]), interaction.guild.id, 'flag_list')
                        await interaction.response.edit_message(
                            content=f"**{Translator.translate(f'flagged_list', interaction.guild, server=interaction.guild.name, page_num=page_num + 1, pages=len(pages))}**```\n{page}```",
                            view=view)
                elif t == 'word_flag_list':
                    cog = self.bot.get_cog('Moderation')
                    if cog is not None:
                        censor_list = Configuration.get_var(interaction.guild.id, "FLAGGING", "WORD_LIST")
                        pages = Pages.paginate("\n".join(censor_list))
                        page, view, page_num = SimplePager.get_parts(pages, int(parts[1]), interaction.guild.id, 'word_flag_list')
                        await interaction.response.edit_message(
                            content=f"**{Translator.translate(f'flagged_word_list', interaction.guild, server=interaction.guild.name, page_num=page_num + 1, pages=len(pages))}**```\n{page}```",
                            view=view)
                elif t == 'mass_failures':
                    output = await self.bot.redis_pool.get(f'mass_failures:{parts[3]}')
                    if output is None:
                        await interaction.response.send_message(MessageUtils.assemble(interaction.guild_id, 'NO', 'view_expired'), ephemeral=True)
                    else:
                        pages = Pages.paginate(output, prefix='```\n', suffix='```')
                        content, view, page_num = SimplePager.get_parts(pages, int(parts[1]), interaction.guild_id,
                                                                        f'mass_failures:{parts[3]}:{parts[4]}')
                        await interaction.response.edit_message(
                            content=f"**{Translator.translate(f'mass_failures_{parts[4]}', interaction.guild_id, page_num=page_num+1, pages=len(pages))}**{content}", view=view)
            elif cid.startswith('einf_search:'):
                parts = cid.split(':')
                uid = int(parts[1])
                old_page = int(parts[2])
                t = parts[3]

                if t == 'first_page':
                    page, current, pages, query, fields = await get_ephemeral_cached_page(interaction, uid, 0)
                    await interaction.response.edit_message(
                        content=await InfractionUtils.assemble_message(interaction.guild_id, page, query, current,
                                                                       pages),
                        view=EphemeralInfSearch(filters=fields, pages=pages, current_page=current, guild_id=interaction.guild_id, userid=uid)
                    )
                elif t == 'prev_page':
                    page, current, pages, query, fields = await get_ephemeral_cached_page(interaction, uid, old_page-1)
                    await interaction.response.edit_message(
                        content=await InfractionUtils.assemble_message(interaction.guild_id, page, query, current,
                                                                       pages),
                        view=EphemeralInfSearch(filters=fields, pages=pages, current_page=current, guild_id=interaction.guild_id, userid=uid)
                    )
                elif t == 'blank':
                    await interaction.response.send_message(Emoji.get_chat_emoji('AE'), ephemeral=True)
                elif t == 'next_page':
                    page, current, pages, query, fields = await get_ephemeral_cached_page(interaction, uid,
                                                                                          old_page + 1)
                    await interaction.response.edit_message(
                        content=await InfractionUtils.assemble_message(interaction.guild_id, page, query, current,
                                                                       pages),
                        view=EphemeralInfSearch(filters=fields, pages=pages, current_page=current, guild_id=interaction.guild_id, userid=uid)
                    )
                elif t == 'last_page':
                    page, current, pages, query, fields = await get_ephemeral_cached_page(interaction, uid,
                                                                                          1000)
                    await interaction.response.edit_message(
                        content=await InfractionUtils.assemble_message(interaction.guild_id, page, query, current,
                                                                       pages),
                        view=EphemeralInfSearch(filters=fields, pages=pages, current_page=current, guild_id=interaction.guild_id, userid=uid)
                    )
        elif interaction.type == InteractionType.application_command:
            if interaction.data["name"] == "Extract user IDs":
                self.bot.metrics.uid_usage.labels(type="channel", cluster=self.bot.cluster).inc()
                await interaction.response.defer(ephemeral=True)
                parts = await Utils.get_user_ids(interaction.data["resolved"]["messages"][interaction.data["target_id"]]["content"])
                if len(parts) > 0:
                    for chunk in Pages.paginate("\n".join(parts), 200):
                        await interaction.followup.send(chunk)
                else:
                    await interaction.followup.send(MessageUtils.assemble(interaction.guild, "NO", "no_uids_found"))
            elif interaction.data["name"] == "Send user IDs to DM":
                self.bot.metrics.uid_usage.labels(type="DM", cluster=self.bot.cluster).inc()
                await interaction.response.defer(ephemeral=True)
                parts = await Utils.get_user_ids(
                    interaction.data["resolved"]["messages"][interaction.data["target_id"]]["content"])
                if len(parts) > 0:
                    try:
                        for chunk in Pages.paginate("\n".join(parts), 200):
                            await interaction.user.send(chunk)
                    except Forbidden:
                        await interaction.followup.send("Unable to send DM")
                    else:
                        await interaction.followup.send("IDs sent in DM")
                else:
                    try:
                        await interaction.user.send(MessageUtils.assemble(interaction.guild, "NO", "no_uids_found"))
                    except Forbidden:
                        await interaction.followup.send("Unable to send DM")
                    else:
                        await interaction.followup.send("IDs sent in DM")
            elif interaction.data["name"] == "Userinfo":
                if await Permissioncheckers.check_permission(self.bot.get_command("userinfo"), interaction.guild, interaction.user, self.bot):
                    t = "allowed"
                    target = interaction.data["target_id"]
                    member = None
                    user_dict = interaction.data["resolved"]["users"][target]
                    user = User(data=user_dict, state=interaction._state)
                    if "members" in interaction.data["resolved"] and target in interaction.data["resolved"]["members"]:
                        member_dict = interaction.data["resolved"]["members"][target]
                        member_dict["user"] = user_dict
                        member = Member(data=member_dict, guild=interaction.guild, state=interaction._state)
                    embed = await Utils.generate_userinfo_embed(user, member, interaction.guild, interaction.user)
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    t = "denied"
                    await interaction.response.send_message(MessageUtils.assemble(interaction.guild, 'LOCK', 'permission_denied'), ephemeral=True)
                self.bot.metrics.userinfo_usage.labels(type=t, cluster=self.bot.cluster).inc()
            elif interaction.data["name"] == "Search Infractions":
                if await Permissioncheckers.check_permission(self.bot.get_command("inf search"), interaction.guild, interaction.user, self.bot):
                    uid = int(interaction.data["target_id"])
                    t = "allowed"
                    await interaction.response.send_message(MessageUtils.assemble(interaction.guild, 'SEARCH', 'inf_search_compiling'), ephemeral=True)

                    pages = await InfractionUtils.fetch_infraction_pages(interaction.guild.id, uid, 100, ["[user]", "[mod]", "[reason]"], 0)
                    page = await self.bot.wait_for('page_assembled',
                                                   check=lambda l: l['key'] == get_key(interaction.guild.id, uid, ["[user]", "[mod]", "[reason]"], 100) and l['page_num'] == 0)
                    await interaction.edit_original_message(
                        content=await InfractionUtils.assemble_message(interaction.guild.id, page['page'], uid, 0, pages),
                        view=EphemeralInfSearch(filters=["[user]", "[mod]", "[reason]"], pages=pages, guild_id=interaction.guild.id, userid=uid)
                    )
                else:
                    t = "denied"
                    await interaction.response.send_message(MessageUtils.assemble(interaction.guild, 'LOCK', 'permission_denied'), ephemeral=True)
                self.bot.metrics.inf_search_usage.labels(type=t, cluster=self.bot.cluster).inc()


def setup(bot):
    bot.add_cog(Interactions(bot))
