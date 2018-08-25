import asyncio
import random
import time
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import clean_content

from Util import Configuration, Pages, HelpGenerator, Permissioncheckers, Emoji, Translator, Utils, GearbotLogging
from database.DatabaseConnector import LoggedMessage, LoggedAttachment


class Basic:
    permissions = {
        "min": 0,
        "max": 6,
        "required": 0,
        "commands": {}
    }

    def __init__(self, bot):
        self.bot:commands.Bot = bot
        Pages.register("help", self.init_help, self.update_help)
        Pages.register("role", self.init_role, self.update_role)
        self.running = True
        self.bot.loop.create_task(self.taco_eater())

    def __unload(self):
        #cleanup
        Pages.unregister("help")
        Pages.unregister("role")
        self.running = False


    async def __local_check(self, ctx):
        return Permissioncheckers.check_permission(ctx)

    @commands.command(hidden=True)
    async def ping(self, ctx:commands.Context):
        """ping_help"""
        if await self.bot.is_owner(ctx.author):
            t1 = time.perf_counter()
            await ctx.trigger_typing()
            t2 = time.perf_counter()
            await ctx.send(f":hourglass: REST API ping is {round((t2 - t1) * 1000)}ms | Websocket ping is {round(self.bot.latency*1000, 2)}ms :hourglass:")
        else:
            await ctx.send(":ping_pong:")

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def quote(self, ctx:commands.Context, message_id:int):
        """quote_help"""
        embed = None
        async with ctx.typing():
            message = LoggedMessage.get_or_none(messageid=message_id)
            if message is None:
                for guild in self.bot.guilds:
                    for channel in guild.text_channels:
                        try:
                            dmessage: discord.Message = await channel.get_message(message_id)
                            for a in dmessage.attachments:
                                LoggedAttachment.get_or_create(id=a.id, url=a.url,
                                                               isImage=(a.width is not None or a.width is 0),
                                                               messageid=message.id)
                            message = LoggedMessage.create(messageid=message_id, content=dmessage.content, author=dmessage.author.id, timestamp = dmessage.created_at.timestamp(), channel=channel.id, server=dmessage.guild.id)
                        except Exception as ex:
                            #wrong channel
                            pass
                        if message is not None:
                            break
            if message is not None:
                channel = self.bot.get_channel(message.channel)
                attachment = None
                attachments = LoggedAttachment.select().where(LoggedAttachment.messageid == message_id)
                if len(attachments) == 1:
                    attachment = attachments[0]
                embed = discord.Embed(colour=discord.Color(0xd5fff), timestamp=datetime.utcfromtimestamp(message.timestamp))
                if message.content is None or message.content == "":
                    if attachment is not None:
                        if attachment.isImage:
                            embed.set_image(url=attachment.url)
                        else:
                            embed.add_field(name=Translator.translate("attachment_link", ctx), value=attachment.url)
                else:
                    description = message.content
                    embed = discord.Embed(colour=discord.Color(0xd5fff), description=description, timestamp=datetime.utcfromtimestamp(message.timestamp))
                    embed.add_field(name="​", value=f"https://discordapp.com/channels/{channel.guild.id}/{channel.id}/{message_id}")
                    if attachment is not None:
                        if attachment.isImage:
                            embed.set_image(url=attachment.url)
                        else:
                            embed.add_field(name=Translator.translate("attachment_link", ctx), value=attachment.url)
                try:
                    user = await commands.MemberConverter().convert(ctx, message.author)
                except:
                    user = await ctx.bot.get_user_info(message.author)
                embed.set_author(name=user.name, icon_url=user.avatar_url)
                embed.set_footer(text=Translator.translate("quote_footer", ctx, channel=self.bot.get_channel(message.channel).name, user=Utils.clean(ctx.author.display_name), message_id=message_id))
        if embed is None:
            await ctx.send(Translator.translate("quote_not_found", ctx))
        else:
            if channel.is_nsfw() and not ctx.channel.is_nsfw():
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('quote_nsfw_refused', ctx)}")
                return
            await ctx.send(embed=embed)
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                await ctx.message.delete()

    @commands.command()
    async def coinflip(self, ctx, *, thing:str = ""):
        """coinflip_help"""
        if thing == "":
            thing = Translator.translate("coinflip_default", ctx)
        outcome = random.randint(1, 2)
        if outcome == 1 or ("mute" in thing and "vos" in thing):
            await ctx.send(Translator.translate("coinflip_yes", ctx, thing=thing))
        else:
            await ctx.send(Translator.translate("coinflip_no", ctx, thing=thing))

    async def init_role(self, ctx):
        pages = self.gen_role_pages(ctx.guild)
        page = pages[0]
        embed = discord.Embed(title=Translator.translate("assignable_roles", ctx, server_name=ctx.guild.name, page_num=1, page_count=len(pages)), colour=discord.Colour(0xbffdd), description=page)
        return None, embed, len(pages) > 1

    async def update_role(self, ctx, message, page_num, action, data):
        pages = self.gen_role_pages(message.guild)
        page, page_num = Pages.basic_pages(pages, page_num, action)
        embed = discord.Embed(title=Translator.translate("assignable_roles", ctx, server_name=ctx.guild.name, page_num=page_num + 1, page_count=len(pages)), color=0x54d5ff, description=page)
        return None, embed, page_num

    def gen_role_pages(self, guild:discord.Guild):
        pages = []
        current_roles = ""
        roles = Configuration.getConfigVar(guild.id, "SELF_ROLES")
        for role in roles:
            if len(current_roles + f"<@&{role}>\n\n") > 300:
                pages.append(current_roles)
                current_roles = ""
            current_roles += f"<@&{role}>\n\n"
        pages.append(current_roles)
        return pages

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def role(self, ctx:commands.Context, *, role:str = None):
        """role_help"""
        if role is None:
            await Pages.create_new("role", ctx)
        else:
            try:
                role = await commands.RoleConverter().convert(ctx, role)
            except Exception as ex:
                await ctx.send(Translator.translate("role_not_found", ctx))
            else:
                roles = Configuration.getConfigVar(ctx.guild.id, "SELF_ROLES")
                if role.id in roles:
                    if role in ctx.author.roles:
                        await ctx.author.remove_roles(role)
                        await ctx.send(Translator.translate("role_left", ctx, role_name=role.name))
                    else:
                        await ctx.author.add_roles(role)
                        await ctx.send(Translator.translate("role_joined", ctx, role_name=role.name))
                else:
                    await ctx.send(Translator.translate("role_not_allowed", ctx))

    # @commands.command()
    # async def test(self, ctx):
    #    async def send(message):
    #         await ctx.send(message)
    #    await Confirmation.confirm(ctx, "You sure?", on_yes=lambda : send("Doing the thing!"), on_no=lambda: send("Not doing the thing!"))


    @commands.command()
    async def help(self, ctx, *, query:str=None):
        """help_help"""
        await Pages.create_new("help", ctx, query=query)

    async def init_help(self, ctx, query):
        pages = await self.get_help_pages(ctx, query)
        if pages is None:
            query_clean = await clean_content().convert(ctx, query)
            return await clean_content().convert(ctx, Translator.translate("help_not_found" if len(query) < 1500 else "help_no_wall_allowed", ctx, query=query_clean)), None, False
        return f"**{Translator.translate('help_title', ctx, page_num=1, pages=len(pages))}**```diff\n{pages[0]}```", None, len(pages) > 1

    async def update_help(self, ctx, message, page_num, action, data):
        pages = await self.get_help_pages(ctx, data["query"])
        page, page_num = Pages.basic_pages(pages, page_num, action)
        return f"**{Translator.translate('help_title', ctx, page_num=page_num + 1, pages=len(pages))}**```diff\n{page}```", None, page_num

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


    async def on_guild_role_delete(self, role:discord.Role):
        roles = Configuration.getConfigVar(role.guild.id, "SELF_ROLES")
        if role.id in roles:
            roles.remove(role.id)
            Configuration.saveConfig(role.guild.id)

    async def taco_eater(self):
        """A person can eat a taco every 5 mins, we run every 5s"""
        GearbotLogging.info("Time to start munching on some 🌮")
        while self.running:
            self.bot.eaten += len(self.bot.users) / 60
            await asyncio.sleep(5)
        GearbotLogging.info("Cog terminated, guess no more 🌮 for people")

def setup(bot):
    bot.add_cog(Basic(bot))
