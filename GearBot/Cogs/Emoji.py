import asyncio

import discord
from discord import HTTPException, InvalidArgument, Embed, Role, Emoji
from discord.ext import commands
from discord.ext.commands import Greedy

from Cogs.BaseCog import BaseCog
from Util import Permissioncheckers, MessageUtils, Translator, Pages, Utils
from Util.Converters import EmojiName


class Emoji(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)

        Pages.register("emoji", self.emoji_list_init, self.emoji_list_update)

    def cog_unload(self):
        Pages.unregister("emoji")

    async def cog_check (self, ctx):
        return Permissioncheckers.check_permission(ctx.command, ctx.guild, ctx.author) or ctx.channel.permissions_for(ctx.author).manage_emojis

    @commands.group(aliases=["emote"])
    @commands.guild_only()
    async def emoji(self, ctx):
        """emoji_help"""
        if ctx.subcommand_passed is None:
            await ctx.invoke(self.bot.get_command("help"), query="emoji")

    @emoji.command("list")
    async def emoji_list(self, ctx):
        await Pages.create_new(self.bot, "emoji", ctx)

    async def emoji_list_init(self, ctx):
        return None, self.gen_emoji_page(ctx.guild, 0), len(ctx.guild.emojis) > 0

    async def emoji_list_update(self, ctx, message, page_num, action, data):
        page_count = len(message.guild.emojis) + 1
        if action == "PREV":
            page_num -= 1
        elif action == "NEXT":
            page_num += 1
        if page_num < 0:
            page_num = page_count - 1
        if page_num >= page_count:
            page_num = 0
        data["page"] = page_num
        return None, self.gen_emoji_page(message.guild, page_num), data

    def gen_emoji_page(self, guild: discord.Guild, page):
        se = sorted(guild.emojis, key=lambda e: e.name)

        embed = Embed(color=0x2db1f3)
        embed.set_author(name=Translator.translate('emoji_server', guild, server=guild.name, page=page + 1,
                                                   pages=len(guild.emojis) + 1), url=guild.icon_url)
        if page is 0:
            for chunk in Utils.chunks(se, 18):
                embed.add_field(name="\u200b", value=" ".join(str(e) for e in chunk))
            animated = set()
            static = set()
            for e in guild.emojis:
                (animated if e.animated else static).add(str(e))
            max_emoji = guild.emoji_limit
            embed.add_field(name=Translator.translate('static_emoji', guild), value=f"{len(static)} / {max_emoji}")
            embed.add_field(name=Translator.translate('animated_emoji', guild), value=f"{len(animated)} / {max_emoji}")
        else:
            self.add_emoji_info(guild, embed, se[page - 1])

        return embed

    @staticmethod
    def add_emoji_info(location, embed, emoji):
        embed.set_image(url=emoji.url)
        embed.add_field(name=Translator.translate('id', location), value=emoji.id)
        embed.add_field(name=Translator.translate('name', location), value=emoji.name)
        for t in ["require_colons", "animated", "managed"]:
            v = str(getattr(emoji, t)).lower()
            embed.add_field(name=Translator.translate(f'emoji_{t}', location),
                            value=MessageUtils.assemble(location, 'YES' if v == 'true' else 'NO', v))
        if len(emoji.roles) > 0:
            roles = ", ".join(r.mention for r in emoji.roles)
        else:
            roles = Translator.translate("emoji_role_no_restrictions", location)
        embed.add_field(name=Translator.translate("emoji_role_restrictions", location), value=roles)

    @emoji.command("info")
    @commands.bot_has_permissions(embed_links=True)
    async def emoji_info(self, ctx, emoji: Emoji):
        embed = Embed(color=0x2db1f3)
        self.add_emoji_info(ctx, embed, emoji)
        await ctx.send(embed=embed)

    @emoji.command("add", aliases=["upload", "create"])
    @commands.bot_has_permissions(manage_emojis=True, embed_links=True)
    async def emoji_add(self, ctx, name: EmojiName, roles: Greedy[Role] = None):
        """emoji_upload_help"""
        if len(ctx.message.attachments) is 0:
            await MessageUtils.send_to(ctx, "NO", "emoji_upload_no_attachments")
        use_counter = len(ctx.message.attachments) > 1
        counter = 1
        for attachment in ctx.message.attachments:
            message = await MessageUtils.send_to(ctx, "YES", "emoji_upload_downloading")
            async with self.bot.aiosession.get(attachment.proxy_url) as resp:
                data = await resp.read()
                if len(data) > 256000:
                    return await MessageUtils.try_edit(message, emoji="NO", string_name="emoji_upload_invalid_filesize",
                                                       filesize=round(len(data) / 1000))
                try:
                    emote = await ctx.guild.create_custom_emoji(name=f"{name}{counter}" if use_counter else name, image=data, roles=roles)
                    counter += 1

                    embed = Embed(color=0x2db1f3)
                    self.add_emoji_info(ctx, embed, emote)
                    return await MessageUtils.try_edit(message, emoji="YES", string_name="emoji_upload_success",
                                                       emote=emote, embed=embed)
                except HTTPException as msg:
                    if msg.code == 50035:
                        await MessageUtils.send_to(ctx, 'NO', 'emoji_upload_rejected')
                    elif msg.text is not None and str(msg.text) != "":
                        return await ctx.send(msg.text)
                    else:
                        await MessageUtils.send_to(ctx, 'NO', 'emoji_upload_rejected_no_message')
                except InvalidArgument as msg:
                    return await MessageUtils.try_edit(message, emoji="NO", string_name="emoji_upload_invalid_file")

    @emoji.command(aliases=["change", "rename", "redefine"])
    @commands.bot_has_permissions(manage_emojis=True, embed_links=True)
    async def update(self, ctx, emote: discord.Emoji, new_name: EmojiName):
        """emoji_update_help"""
        try:
            await emote.edit(name=new_name, roles=emote.roles,
                             reason=Translator.translate("emoji_update_reason", ctx.guild.id,
                                                         user=str(ctx.author)))
        except HTTPException as msg:
            await ctx.send(msg.text)
        else:
            await asyncio.sleep(1)  # sleep so the cache can update
            embed = Embed(color=0x2db1f3)
            self.add_emoji_info(ctx, embed, emote)
            await MessageUtils.send_to(ctx, "YES", "emoji_update_success", new_name=new_name,
                                       embed=embed)

    @emoji.command(aliases=["remove", "nuke", "rmv", "del", "👋", "🗑"])
    @commands.bot_has_permissions(manage_emojis=True)
    async def delete(self, ctx, emote: discord.Emoji):
        """emoji_delete_help"""
        try:
            await emote.delete()
            return await MessageUtils.send_to(ctx, "YES", "emoji_delete_success")
        except HTTPException as msg:
            return await ctx.send(msg.text)

    @emoji.group("roles", aliases=["role"])
    async def emoji_roles(self, ctx):
        """emoji_roles_help"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.bot.get_command("help"), query="emoji roles")

    @emoji_roles.command("add")
    @commands.bot_has_permissions(manage_emojis=True, embed_links=True)
    async def emoji_roles_add(self, ctx, emote: discord.Emoji, roles: Greedy[discord.Role] = None):
        if roles is None:
            return MessageUtils.send_to(ctx, 'NO', 'roles_no_roles')
        todo = set()
        refused = set()
        for role in roles:
            (refused if role in emote.roles else todo).add(role)
        new_roles = list(emote.roles)
        new_roles.extend(todo)
        await emote.edit(name=emote.name, roles=new_roles)
        await asyncio.sleep(1)  # sleep so the cache can update
        embed = Embed(color=0x2db1f3)
        self.add_emoji_info(ctx, embed, emote)
        if len(todo) > 0:
            message = MessageUtils.assemble(ctx, "YES", "emoji_roles_add_success", roles=self.pretty_role_list(todo, ctx))
        else:
            message = ""
        if len(refused) > 0:
            message += "\n" + MessageUtils.assemble(ctx, "NO", "emoji_roles_add_role_already_in_list",
                                                    roles=self.pretty_role_list(refused, ctx))
        await ctx.send(message)

    @emoji_roles.command("remove")
    @commands.bot_has_permissions(manage_emojis=True, embed_links=True)
    async def emoji_roles_remove(self, ctx, emote: discord.Emoji, roles: Greedy[discord.Role]):
        if roles is None:
            return MessageUtils.send_to(ctx, 'NO', 'roles_no_roles')
        todo = set()
        refused = set()
        for role in roles:
            (refused if role not in emote.roles else todo).add(role)
        new_roles = list(emote.roles)
        for role in todo:
            new_roles.remove(role)
        await emote.edit(name=emote.name, roles=new_roles)
        await asyncio.sleep(1)  # sleep so the cache can update
        embed = Embed(color=0x2db1f3)
        self.add_emoji_info(ctx, embed, emote)
        message = MessageUtils.assemble(ctx, "YES", "emoji_roles_remove_success",
                                        roles=self.pretty_role_list(todo, ctx))
        if len(refused) > 0:
            message += "\n" + MessageUtils.assemble(ctx, "NO", "emoji_roles_remove_role_not_in_list",
                                                    roles=self.pretty_role_list(refused, ctx))
        await ctx.send(message)

    def pretty_role_list(self, roles, destination):
        out = ", ".join(f"`{role.name}`" for role in roles)
        if len(out) > 900:
            out = Translator.translate('too_many_roles_to_list', destination)
        return out


def setup(bot):
    bot.add_cog(Emoji(bot))
