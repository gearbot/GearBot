import random
import time
from datetime import datetime

import discord
from discord.ext import commands

from Util import Configuration
from database.DatabaseConnector import LoggedMessage, LoggedAttachment


class Basic:

    def __init__(self, bot):
        self.bot:commands.Bot = bot

    def __unload(self):
        #cleanup
        pass

    def __global_check(self, ctx):
        return True

    def __global_check_once(self, ctx):
        return True

    async def __local_check(self, ctx):
        return True

    @commands.command(hidden=True)
    async def ping(self, ctx:commands.Context):
        """Basic ping to see if the bot is still up"""
        if (self.bot.is_owner(ctx.author)):
            t1 = time.perf_counter()
            await ctx.trigger_typing()
            t2 = time.perf_counter()
            await ctx.send(f":hourglass: Gateway ping is {round((t2 - t1) * 1000)}ms :hourglass:")
        else:
            await ctx.send("pong")

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
                            dmessage:discord.Message = await channel.get_message(messageid)
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
                    embed = discord.Embed(colour=discord.Color(0xd5fff), description=message.content, timestamp=datetime.utcfromtimestamp(message.timestamp))
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

    @commands.command()
    async def role(self, ctx:commands.Context, *, role:str = None):
        """Lists self assignable roles or adds/removes [role] from you"""
        if role is None:
            desc = ""
            roles = Configuration.getConfigVar(ctx.guild.id, "SELF_ROLES")
            for role in roles:
                desc = f"{desc}<@&{role}>\n"
            embed = discord.Embed(title="asignable roles", colour=discord.Colour(0xbffdd), description=desc)
            await ctx.send(embed=embed)
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


def setup(bot):
    bot.add_cog(Basic(bot))