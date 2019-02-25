import asyncio
import random
import time
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import clean_content, BadArgument

from Bot.GearBot import GearBot
from Util import Configuration, Pages, HelpGenerator, Permissioncheckers, Emoji, Translator, Utils, GearbotLogging, \
    MessageUtils
from Util.Converters import Message, DiscordUser
from Util.JumboGenerator import JumboGenerator
from Util.Matchers import NUMBER_MATCHER
from database.DatabaseConnector import LoggedAttachment


class Basic:
    permissions = {
        "min": 0,
        "max": 6,
        "required": 0,
        "commands": {
        }
    }

    def __init__(self, bot):
        self.bot: GearBot = bot
        Pages.register("help", self.init_help, self.update_help)
        Pages.register("role", self.init_role, self.update_role)
        self.running = True
        self.bot.loop.create_task(self.taco_eater())

    def __unload(self):
        # cleanup
        Pages.unregister("help")
        Pages.unregister("role")
        self.running = False

    async def __local_check(self, ctx):
        return Permissioncheckers.check_permission(ctx)

    @commands.command()
    async def about(self, ctx):
        """about_help"""
        uptime = datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        days, hours = divmod(hours, 24)
        minutes, seconds = divmod(remainder, 60)
        tacos = "{:,}".format(round(self.bot.eaten))
        user_messages = "{:,}".format(self.bot.user_messages)
        bot_messages = "{:,}".format(self.bot.bot_messages)
        self_messages = "{:,}".format(self.bot.self_messages)
        total = "{:,}".format(sum(len(guild.members) for guild in self.bot.guilds))
        unique = "{:,}".format(len(self.bot.users))
        embed = discord.Embed(colour=discord.Colour(0x00cea2),
                              timestamp=datetime.utcfromtimestamp(time.time()),
                              description=
                              MessageUtils.assemble(ctx, 'DIAMOND', 'about_spinning_gears', duration=Translator.translate('dhms', ctx, days=days, hours=hours, minutes=minutes, seconds=seconds)) + "\n"+
                              MessageUtils.assemble(ctx, 'GOLD', 'about_messages', user_messages=user_messages, bot_messages=bot_messages, self_messages=self_messages) + "\n"+
                              MessageUtils.assemble(ctx, 'IRON', 'about_grinders', errors=self.bot.errors) + "\n" +
                              MessageUtils.assemble(ctx, 'STONE', 'about_commands', commandCount=self.bot.commandCount, custom_command_count=self.bot.custom_command_count) + "\n" +
                              MessageUtils.assemble(ctx, 'WOOD', 'about_guilds', guilds=len(self.bot.guilds)) + "\n" +
                              MessageUtils.assemble(ctx, 'INNOCENT', 'about_users', total=total, unique=unique) + "\n" +
                              MessageUtils.assemble(ctx, 'TACO', 'about_tacos', tacos=tacos) + "\n" +
                              MessageUtils.assemble(ctx, 'TODO', 'about_stats'))

        click_here = Translator.translate('click_here', ctx)
        embed.add_field(name=Translator.translate('support_server', ctx), value=f"[{click_here}](https://discord.gg/vddW3D9)")
        embed.add_field(name=Translator.translate('website', ctx), value=f"[{click_here}](https://gearbot.rocks)")
        embed.add_field(name=f"Github", value=f"[{click_here}](https://github.com/AEnterprise/GearBot)")
        embed.set_footer(text=self.bot.user.name, icon_url=self.bot.user.avatar_url)

        await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def ping(self, ctx: commands.Context):
        """ping_help"""
        if await self.bot.is_owner(ctx.author):
            t1 = time.perf_counter()
            await ctx.trigger_typing()
            t2 = time.perf_counter()
            await ctx.send(
                f":hourglass: REST API ping is {round((t2 - t1) * 1000)}ms | Websocket ping is {round(self.bot.latency*1000, 2)}ms :hourglass:")
        else:
            await ctx.send(":ping_pong:")

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def quote(self, ctx: commands.Context, *, message:Message):
        """quote_help"""
        await ctx.trigger_typing()
        member = message.guild.get_member(ctx.author.id)
        if member is None:
            await MessageUtils.send_to(ctx, 'NO', 'quote_not_visible_to_user')
        else:
            permissions = message.channel.permissions_for(member)
            if permissions.read_message_history and permissions.read_message_history:
                if message.channel.is_nsfw() and not ctx.channel.is_nsfw():
                    await MessageUtils.send_to(ctx, 'NO', 'quote_nsfw_refused')
                else:
                    attachment = None
                    attachments = LoggedAttachment.select().where(LoggedAttachment.messageid == message.id)
                    if len(attachments) == 1:
                        attachment = attachments[0]
                    embed = discord.Embed(colour=discord.Color(0xd5fff),
                                          timestamp=message.created_at)
                    if message.content is None or message.content == "":
                        if attachment is not None:
                            if attachment.isImage:
                                embed.set_image(url=attachment.url)
                            else:
                                embed.add_field(name=Translator.translate("attachment_link", ctx),
                                                value=attachment.url)
                    else:
                        description = message.content
                        embed = discord.Embed(colour=discord.Color(0xd5fff), description=description,
                                              timestamp=message.created_at)
                        embed.add_field(name="​",
                                        value=f"[Jump to message]({message.jump_url})")
                        if attachment is not None:
                            if attachment.isImage:
                                embed.set_image(url=attachment.url)
                            else:
                                embed.add_field(name=Translator.translate("attachment_link", ctx),
                                                value=attachment.url)
                    user = message.author
                    embed.set_author(name=user.name, icon_url=user.avatar_url)
                    embed.set_footer(
                        text=Translator.translate("quote_footer", ctx,
                                                  channel=message.channel.name,
                                                  user=Utils.clean_user(ctx.author), message_id=message.id))
                    await ctx.send(embed=embed)
                    if ctx.channel.permissions_for(ctx.me).manage_messages:
                        await ctx.message.delete()

            else:
                await MessageUtils.send_to(ctx, 'NO', 'quote_not_visible_to_user')




    @commands.command()
    async def coinflip(self, ctx, *, thing: str = ""):
        """coinflip_help"""
        if thing == "":
            thing = Translator.translate("coinflip_default", ctx)
        else:
            thing = await Utils.clean(thing, ctx.guild)
        outcome = random.randint(1, 2)
        if outcome == 1 or ("mute" in thing and "vos" in thing):
            await ctx.send(Translator.translate("coinflip_yes", ctx, thing=thing))
        else:
            await ctx.send(Translator.translate("coinflip_no", ctx, thing=thing))

    async def init_role(self, ctx):
        pages = self.gen_role_pages(ctx.guild)
        page = pages[0]
        emoji = []
        for i in range(10 if len(pages) > 1 else round(len(page.splitlines()) / 2)):
            emoji.append(Emoji.get_emoji(str(i + 1)))
        embed = discord.Embed(
            title=Translator.translate("assignable_roles", ctx, server_name=ctx.guild.name, page_num=1,
                                       page_count=len(pages)), colour=discord.Colour(0xbffdd), description=page)
        return None, embed, len(pages) > 1, emoji

    async def update_role(self, ctx, message, page_num, action, data):
        pages = self.gen_role_pages(message.guild)
        page, page_num = Pages.basic_pages(pages, page_num, action)
        embed = discord.Embed(
            title=Translator.translate("assignable_roles", ctx, server_name=message.channel.guild.name, page_num=page_num + 1,
                                       page_count=len(pages)), color=0x54d5ff, description=page)
        return None, embed, page_num

    def gen_role_pages(self, guild: discord.Guild):
        roles = Configuration.get_var(guild.id, "SELF_ROLES")
        current_roles = ""
        count = 1
        for role in roles:
            current_roles += f"{count}) <@&{role}>\n\n"
            count += 1
            if count > 10:
                count = 1
        return Pages.paginate(current_roles, max_lines=20)

    @commands.command(aliases=["selfrole", "self_roles", "selfroles"])
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def self_role(self, ctx: commands.Context, *, role: str = None):
        """role_help"""
        if role is None:
            await Pages.create_new("role", ctx)
        else:
            try:
                role = await commands.RoleConverter().convert(ctx, role)
            except BadArgument as ex:
                await ctx.send(Translator.translate("role_not_found", ctx))
            else:
                roles = Configuration.get_var(ctx.guild.id, "SELF_ROLES")
                if role.id in roles:
                    try:
                        if role in ctx.author.roles:
                            await ctx.author.remove_roles(role)
                            await ctx.send(Translator.translate("role_left", ctx, role_name=role.name))
                        else:
                            await ctx.author.add_roles(role)
                            await ctx.send(Translator.translate("role_joined", ctx, role_name=role.name))
                    except discord.Forbidden:
                        await ctx.send(
                            f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mute_role_to_high', ctx, role=role.name)}")
                else:
                    await ctx.send(Translator.translate("role_not_allowed", ctx))

    # @commands.command()
    # async def test(self, ctx):
    #    async def send(message):
    #         await ctx.send(message)
    #    await Confirmation.confirm(ctx, "You sure?", on_yes=lambda : send("Doing the thing!"), on_no=lambda: send("Not doing the thing!"))

    @commands.command()
    async def help(self, ctx, *, query: str = None):
        """help_help"""
        await Pages.create_new("help", ctx, query=query)

    async def init_help(self, ctx, query):
        pages = await self.get_help_pages(ctx, query)
        if pages is None:
            query_clean = await clean_content().convert(ctx, query)
            return await clean_content().convert(ctx, Translator.translate(
                "help_not_found" if len(query) < 1500 else "help_no_wall_allowed", ctx,
                query=query_clean)), None, False, []
        eyes = Emoji.get_chat_emoji('EYES')
        return f"{eyes} **{Translator.translate('help_title', ctx, page_num=1, pages=len(pages))}** {eyes}```diff\n{pages[0]}```", None, len(
            pages) > 1, []

    async def update_help(self, ctx, message, page_num, action, data):
        pages = await self.get_help_pages(ctx, data["query"])
        page, page_num = Pages.basic_pages(pages, page_num, action)
        eyes = Emoji.get_chat_emoji('EYES')
        return f"{eyes} **{Translator.translate('help_title', ctx, page_num=page_num + 1, pages=len(pages))}**{eyes}```diff\n{page}```", None, page_num

    async def get_help_pages(self, ctx, query):
        if query is None:
            return await HelpGenerator.command_list(self.bot, ctx)
        else:
            if query in self.bot.cogs:
                return await HelpGenerator.gen_cog_help(self.bot, ctx, query)
            else:
                target = self.bot
                layers = query.split(" ")
                while len(layers) > 0:
                    layer = layers.pop(0)
                    if hasattr(target, "all_commands") and layer in target.all_commands.keys():
                        target = target.all_commands[layer]
                    else:
                        target = None
                        break
                if target is not None and target is not self.bot.all_commands:
                    return await HelpGenerator.gen_command_help(self.bot, ctx, target)

        return None

    @commands.command()
    @commands.bot_has_permissions(attach_files=True)
    async def jumbo(self, ctx, *, emojis: str):
        """Jumbo emoji"""
        await JumboGenerator(ctx, emojis).generate()

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def dog(self, ctx):
        """dog_help"""
        await ctx.trigger_typing()
        future_fact = self.get_json("https://dog-api.kinduff.com/api/facts?number=1")
        key = Configuration.get_master_var("DOG_KEY", "")
        future_dog = self.get_json("https://api.thedogapi.com/v1/images/search?limit=1&size=full", {'x-api-key': key},
                                   key != "")
        fact_json, dog_json = await asyncio.gather(future_fact, future_dog)
        embed = discord.Embed(description=fact_json["facts"][0])
        if key != "":
            embed.set_image(url=dog_json[0]["url"])
        await ctx.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def cat(self, ctx):
        """cat_help"""
        await ctx.trigger_typing()
        future_fact = self.get_json("https://catfact.ninja/fact")
        key = Configuration.get_master_var("CAT_KEY", "")
        future_cat = self.get_json("https://api.thecatapi.com/v1/images/search?limit=1&size=full", {'x-api-key' : key}, key != "")
        fact_json, cat_json = await asyncio.gather(future_fact, future_cat)
        embed = discord.Embed(description=fact_json["fact"])
        if  key != "":
            embed.set_image(url=cat_json[0]["url"])
        await ctx.send(embed=embed)




    @commands.command()
    async def uid(self, ctx, *, text:str):
        """uid_help"""
        parts = set()
        for p in set(NUMBER_MATCHER.findall(text)):
            try:
                parts.add(str((await DiscordUser(id_only=True).convert(ctx, p)).id))
            except BadArgument:
                pass
        if len(parts) > 0:
            await ctx.send("\n".join(parts))
        else:
            await MessageUtils.send_to(ctx, "NO", "no_uids_found")

    async def get_json(self, link, headers=None, do_request=True):
        if do_request:
            async with self.bot.aiosession.get(link, headers=headers) as reply:
                return await reply.json()


    async def on_guild_role_delete(self, role: discord.Role):
        roles = Configuration.get_var(role.guild.id, "SELF_ROLES")
        if role.id in roles:
            roles.remove(role.id)
            Configuration.save(role.guild.id)

    async def taco_eater(self):
        """A person can eat a taco every 5 mins, we run every 5s"""
        GearbotLogging.info("Time to start munching on some 🌮")
        while self.running:
            self.bot.eaten += len(self.bot.users) / 60
            await asyncio.sleep(5)
        GearbotLogging.info("Cog terminated, guess no more 🌮 for people")

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        if guild.me.id == payload.user_id:
            return
        if str(payload.message_id) not in Pages.known_messages:
            return
        info = Pages.known_messages[str(payload.message_id)]
        if info["type"] != "role":
            return
        try:
            message = await self.bot.get_channel(payload.channel_id).get_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden):
            pass
        else:
            for i in range(10):
                e = str(Emoji.get_emoji(str(i + 1)))
                if str(payload.emoji) == e:
                    roles = Configuration.get_var(guild.id, "SELF_ROLES")
                    channel = self.bot.get_channel(payload.channel_id)
                    number = info['page'] * 10 + i
                    if number >= len(roles):
                        if channel.permissions_for(channel.guild.me).send_messages:
                            await MessageUtils.send_to(channel, "NO", "role_not_on_page", requested=number+1, max=len(roles) % 10, delete_after=10)
                        return
                    role = guild.get_role(roles[number])
                    if role is None:
                        return
                    member = guild.get_member(payload.user_id)
                    try:
                        if role in member.roles:
                            await member.remove_roles(role)
                            added = False
                        else:
                            await member.add_roles(role)
                            added = True
                    except discord.Forbidden:
                        emessage = f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mute_role_to_high', payload.guild_id, role=role.name)}"
                        try:
                            await channel.send(emessage)
                        except discord.Forbidden:
                            try:
                                member.send(emessage)
                            except discord.Forbidden:
                                pass
                    else:
                        try:
                            action_type = 'role_joined' if added else 'role_left'
                            await channel.send(f"{member.mention} {Translator.translate(action_type, payload.guild_id, role_name=role.name)}", delete_after=10)
                        except discord.Forbidden:
                            pass

                    if channel.permissions_for(guild.me).manage_messages:
                        await message.remove_reaction(payload.emoji, member)
                    break


def setup(bot):
    bot.add_cog(Basic(bot))
