import random
import time
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import clean_content

from Util import Configuration, Confirmation, Pages, HelpGenerator
from database.DatabaseConnector import LoggedMessage, LoggedAttachment


class Basic:

    def __init__(self, bot):
        self.bot:commands.Bot = bot
        Pages.register("help", self.init_help, self.update_help)
        Pages.register("role", self.init_role, self.update_role)

    def __unload(self):
        #cleanup
        Pages.unregister("help")

    def __global_check(self, ctx):
        return True

    def __global_check_once(self, ctx):
        return True

    async def __local_check(self, ctx):
        return True

    @commands.command(hidden=True)
    async def ping(self, ctx:commands.Context):
        """Basic ping to see if the bot is still up"""
        if await self.bot.is_owner(ctx.author):
            t1 = time.perf_counter()
            await ctx.trigger_typing()
            t2 = time.perf_counter()
            await ctx.send(f":hourglass: Gateway ping is {round((t2 - t1) * 1000)}ms :hourglass:")
        else:
            await ctx.send(":ping_pong:")

    @commands.command()
    async def quote(self, ctx:commands.Context, messageid:int):
        """Quotes the requested message"""
        embed = None
        async with ctx.typing():
            message = LoggedMessage.get_or_none(messageid=messageid)
            if message is None:
                for guild in self.bot.guilds:
                    for channel in guild.text_channels:
                        try:
                            dmessage: discord.Message = await channel.get_message(messageid)
                            for a in dmessage.attachments:
                                LoggedAttachment.get_or_create(id=a.id, url=a.url,
                                                               isImage=(a.width is not None or a.width is 0),
                                                               messageid=message.id)
                            message = LoggedMessage.create(messageid=messageid, content=dmessage.content, author=dmessage.author.id, timestamp = dmessage.created_at.timestamp(), channel=channel.id)
                        except Exception as ex:
                            #wrong channel
                            pass
                        if message is not None:
                            break
            if message is not None:
                attachment = None
                attachments = LoggedAttachment.select().where(LoggedAttachment.messageid == messageid)
                if len(attachments) == 1:
                    attachment = attachments[0]
                embed = discord.Embed(colour=discord.Color(0xd5fff), timestamp=datetime.utcfromtimestamp(message.timestamp))
                if message.content is None or message.content == "":
                    if attachment is not None:
                        if attachment.isImage:
                            embed.set_image(url=attachment.url)
                        else:
                            embed.add_field(name="Attachment link", value=attachment.url)
                else:
                    description = message.content
                    embed = discord.Embed(colour=discord.Color(0xd5fff), description=description, timestamp=datetime.utcfromtimestamp(message.timestamp))
                    channel = self.bot.get_channel(message.channel)
                    embed.add_field(name="​", value=f"https://discordapp.com/channels/{channel.guild.id}/{channel.id}/{messageid}")
                    if attachment is not None:
                        if attachment.isImage:
                            embed.set_image(url=attachment.url)
                        else:
                            embed.add_field(name="Attachment link", value=attachment.url)
                try:
                    user = await commands.MemberConverter().convert(ctx, message.author)
                except:
                    user = await ctx.bot.get_user_info(message.author)
                embed.set_author(name=user.name, icon_url=user.avatar_url)
                embed.set_footer(text=f"Sent in #{self.bot.get_channel(message.channel).name} | Quote requested by {ctx.author.display_name} | {messageid}")
        if embed is None:
            await ctx.send("I was unable to find that message anywhere, is it somewhere i can't see?")
        else:
            await ctx.send(embed=embed)
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                await ctx.message.delete()

    @commands.command()
    async def coinflip(self, ctx, *, thing:str = "do the thing"):
        """Random decision making"""
        outcome = random.randint(1, 2)
        if outcome == 1 or ("mute" in thing and "vos" in thing):
            await ctx.send(f"Yes, you should absolutely {thing}")
        else:
            await ctx.send(f"No you should probably not {thing}")

    async def init_role(self, ctx):
        pages = self.gen_role_pages(ctx.guild)
        page = pages[0]
        embed = discord.Embed(title=f"{ctx.guild.name} assignable roles (1/{len(pages)})", colour=discord.Colour(0xbffdd), description=page)
        return None, embed, len(pages) > 1

    async def update_role(self, ctx, message, page_num, action, data):
        pages = self.gen_role_pages(message.guild)
        page, page_num = Pages.basic_pages(pages, page_num, action)
        embed = discord.Embed(title=f"{message.guild.name} assignable roles ({page_num + 1}/{len(pages)})", color=0x54d5ff, description=page)
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
    async def role(self, ctx:commands.Context, *, role:str = None):
        """Lists self assignable roles or adds/removes [role] from you"""
        if role is None:
            await Pages.create_new("role", ctx)
        else:
            try:
                role = await commands.RoleConverter().convert(ctx, role)
            except Exception as ex:
                await ctx.send("Unable to find that role.")
            else:
                roles = Configuration.getConfigVar(ctx.guild.id, "SELF_ROLES")
                if role.id in roles:
                    if role in ctx.author.roles:
                        await ctx.author.remove_roles(role)
                        await ctx.send(f"You left the {role.name} role.")
                    else:
                        await ctx.author.add_roles(role)
                        await ctx.send(f"Welcome to the {role.name} role!")
                else:
                    await ctx.send("You are not allowed to add this role to yourself")

    @commands.command()
    async def test(self, ctx):
       async def send(message):
            await ctx.send(message)
       await Confirmation.confirm(ctx, "You sure?", on_yes=lambda : send("Doing the thing!"), on_no=lambda: send("Not doing the thing!"))


    @commands.command()
    async def help(self, ctx, *, query:str=None):
        await Pages.create_new("help", ctx, query=query)

    async def init_help(self, ctx, query):
        pages = await self.get_help_pages(ctx, query)
        if pages is None:
            return await clean_content().convert(ctx, f'I can\'t seem to find any cog or command named "{query}"'), None, False
        return f"**Gearbot help 1/{len(pages)}**```diff\n{pages[0]}```", None, len(pages) > 1

    async def update_help(self, ctx, message, page_num, action, data):
        pages = await self.get_help_pages(ctx, data["query"])
        page, page_num = Pages.basic_pages(pages, page_num, action)
        return f"**Gearbot help {page_num+1}/{len(pages)}**```diff\n{page}```", None, page_num

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
                    if layer in target.all_commands.keys():
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

def setup(bot):
    bot.add_cog(Basic(bot))