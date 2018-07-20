import asyncio
import datetime
import time
import traceback
from concurrent.futures import CancelledError

import discord
from discord.ext import commands
from discord.ext.commands import BadArgument

from Util import Permissioncheckers, Configuration, Utils, GearbotLogging, Pages, InfractionUtils, Emoji
from Util.Converters import BannedMember


class Moderation:


    def __init__(self, bot):
        self.bot:commands.Bot = bot
        bot.mutes = self.mutes = Utils.fetchFromDisk("mutes")
        self.running = True
        self.bot.loop.create_task(unmuteTask(self))
        Pages.register("roles", self.roles_init, self.roles_update)

    def __unload(self):
        Utils.saveToDisk("mutes", self.mutes)
        self.running = False
        Pages.unregister("roles")

    async def __local_check(self, ctx):
        return Permissioncheckers.isServerMod(ctx)


    async def roles_init(self, ctx):
        pages = self.gen_roles_pages(ctx.guild)
        page = pages[0]
        embed = discord.Embed(title=ctx.guild.name + " roles", color=0x54d5ff)
        embed.add_field(name="\u200b", value=page["roles"], inline=True)
        embed.add_field(name="\u200b", value=page["ids"], inline=True)
        return None, embed, len(pages) > 1

    async def roles_update(self, ctx, message, page_num, action, data):
        pages = self.gen_roles_pages(message.guild)
        page, page_num = Pages.basic_pages(pages, page_num, action)
        embed = discord.Embed(title=message.guild.name + " roles", color=0x54d5ff)
        embed.add_field(name="\u200b", value=page["roles"], inline=True)
        embed.add_field(name="\u200b", value=page["ids"], inline=True)
        return None, embed, page_num

    def gen_roles_pages(self, guild:discord.Guild):
        pages = []
        current_roles = ""
        current_ids = ""
        for role in guild.roles:
            if len(current_roles + f"<@&{role.id}>\n\n") > 300:
                pages.append({
                    "roles": current_roles,
                    "ids": current_ids
                })
                current_ids = ""
                current_roles = ""
            current_roles += f"<@&{role.id}>\n\n"
            current_ids += str(role.id) + "\n\n"
        pages.append({
            "roles": current_roles,
            "ids": current_ids
        })
        return pages
    @commands.command()
    @commands.guild_only()
    async def roles(self, ctx:commands.Context):
        """Lists all roles on the server and their IDs, useful for configuring without having to ping that role"""
        await Pages.create_new("roles", ctx)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason="No reason given."):
        """Kicks an user from the server."""
        self.bot.data["forced_exits"].append(user.id)
        if (ctx.author != user and user != ctx.bot.user and ctx.author.top_role > user.top_role) or ctx.guild.owner == ctx.author:
            await ctx.guild.kick(user, reason=f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}")
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {user.name}#{user.discriminator} (`{user.id}`) was kicked. Reason: `{reason}`")
            await GearbotLogging.logToModLog(ctx.guild, f":boot: {user.name}#{user.discriminator} (`{user.id}`) was kicked by {ctx.author.name}#{ctx.author.discriminator}. Reason: `{reason}`")
            InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Kick", reason)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} You are not allowed to kick {user.name}#{user.discriminator}")

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx:commands.Context, user: discord.Member, *, reason="No reason given"):
        """Bans an user from the server."""
        if (ctx.author != user and user != ctx.bot.user and ctx.author.top_role > user.top_role) or ctx.guild.owner == ctx.author:
            self.bot.data["forced_exits"].append(user.id)
            await ctx.guild.ban(user, reason=f"Moderator: {ctx.author.name} ({ctx.author.id}) Reason: {reason}", delete_message_days=0)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {user.name}#{user.discriminator} (`{user.id}`) was banned. Reason: `{reason}`")
            await GearbotLogging.logToModLog(ctx.guild, f":door: {user.name} (`{user.id}`) was banned by {ctx.author.name}#{ctx.author.discriminator}. Reason: `{reason}`")
            InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Ban ", reason)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} You are not allowed to ban {user.name}#{user.discriminator}")

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def forceban(self, ctx:commands.Context, user_id: int, *, reason="No reason given"):
        """Bans a user even if they are not in the server"""
        try:
            member = await commands.MemberConverter().convert(ctx, str(user_id))
        except BadArgument:
            user = await ctx.bot.get_user_info(user_id)
            if user == ctx.author or user == ctx.bot.user:
                await ctx.send("You cannot ban that user!")
            else:
                await ctx.guild.ban(user, reason=f"Moderator: {ctx.author.name} ({ctx.author.id}) Reason: {reason}", delete_message_days=0)
                await ctx.send(f"{Emoji.get_chat_emoji('YES')} {user.name}#{user.discriminator} (`{user.id}`) was banned. Reason: `{reason}`")
                await GearbotLogging.logToModLog(ctx.guild, f":door: {user.name}#{user.discriminator} (`{user.id}`) was force banned by {ctx.author.name}#{ctx.author.discriminator}. Reason: `{reason}`")
                InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Fban", reason)
        else:
            await ctx.send(f":warning: {member.name} is on this server, executing regular ban command instead")
            await ctx.invoke(self.ban, member, reason=reason)


    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, msgs: int):
        """Purges up to 100 messages in this channel."""
        if msgs > 100:
            await ctx.send("You can only purge 100 messages at a time.")
        else:
            deleted = await ctx.channel.purge(limit=msgs)
            await ctx.send(f"Deleted {(len(deleted))} message(s)!")

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, member: BannedMember, *, reason="No reason given"):
        """Unbans an user from the server."""
        self.bot.data["unbans"].append(member.user.id)
        await ctx.guild.unban(member.user, reason=f"Moderator: {ctx.author.name} ({ctx.author.id}) Reason: {reason}")
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} {member.user.name}#{member.user.discriminator} (`{member.user.id}`) has been unbanned. Reason: `{reason}`")
        await GearbotLogging.logToModLog(ctx.guild, f"<:gearInnocent:465177981287923712> {member.user.name}#{member.user.discriminator} (`{member.user.id}`) was un-banned by {ctx.author.name}#{ctx.author.discriminator}. Reason: `{reason}`")
        InfractionUtils.add_infraction(ctx.guild.id, member.user.id, ctx.author.id, "Unban", reason)
        # This should work even if the user isn't cached


    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx:commands.Context, target:discord.Member, durationNumber:int, durationIdentifier:str, *, reason="No reason provided"):
        """Temporary mutes someone"""
        roleid = Configuration.getConfigVar(ctx.guild.id, "MUTE_ROLE")
        if roleid is 0:
            await ctx.send(f":warning: Unable to comply, you have not told me what role i can use to mute people, but i can still kick {target.mention} if you want while a server admin tells me what role i can use")
        else:
            role = discord.utils.get(ctx.guild.roles, id=roleid)
            if role is None:
                await ctx.send(f":warning: Unable to comply, someone has removed the role i was told to use, but i can still kick {target.mention} while a server admin makes a new role for me to use")
            else:
                if (ctx.author != target and target != ctx.bot.user and ctx.author.top_role > target.top_role) or ctx.guild.owner == ctx.author:
                    duration = Utils.convertToSeconds(durationNumber, durationIdentifier)
                    until = time.time() + duration
                    await target.add_roles(role, reason=f"{reason}, as requested by {ctx.author.name}")
                    if not str(ctx.guild.id) in self.mutes:
                        self.mutes[str(ctx.guild.id)] = dict()
                    self.mutes[str(ctx.guild.id)][str(target.id)] = until
                    await ctx.send(f"{Emoji.get_chat_emoji('MUTE')} {target.display_name} has been muted")
                    Utils.saveToDisk("mutes", self.mutes)
                    await GearbotLogging.logToModLog(ctx.guild, f"{Emoji.get_chat_emoji('MUTE')} {target.name}#{target.discriminator} (`{target.id}`) has been muted by {ctx.author.name} for {durationNumber} {durationIdentifier}: {reason}")
                    InfractionUtils.add_infraction(ctx.guild.id, target.id, ctx.author.id, "Mute", reason)
                else:
                    await ctx.send(f"{Emoji.get_chat_emoji('NO')} You are not allowed to mute {target.name}#{target.discriminator}")

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx:commands.Context, target:discord.Member, *, reason="No reason provided"):
        """Lifts a mute"""
        roleid = Configuration.getConfigVar(ctx.guild.id, "MUTE_ROLE")
        if roleid is 0:
            await ctx.send(f"The mute feature has been dissabled on this server, as such i cannot unmute that person")
        else:
            role = discord.utils.get(ctx.guild.roles, id=roleid)
            if role is None:
                await ctx.send(f":warning: Unable to comply, the role i've been told to use for muting no longer exists")
            else:
                await target.remove_roles(role, reason=f"Unmuted by {ctx.author.name}, {reason}")
                await ctx.send(f"{target.display_name} has been unmuted")
                await GearbotLogging.logToModLog(ctx.guild, f"<:gearInnocent:465177981287923712> {target.name}#{target.discriminator} (`{target.id}`) has been unmuted by {ctx.author.name}")
                InfractionUtils.add_infraction(ctx.guild.id, target.id, ctx.author.id, "Unmute", reason)

    @commands.command()
    async def userinfo(self, ctx: commands.Context, user: str = None):
        """Shows information about the chosen user"""
        if user == None:
            user = ctx.author
            member = ctx.guild.get_member(user.id)
        if user != ctx.author:
            try:
                member = await commands.MemberConverter().convert(ctx, user)
                user = member
            except:
                user = await ctx.bot.get_user_info(int(user))
                member = None
        embed = discord.Embed(color=0x7289DA, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar_url)
        embed.add_field(name="Name", value=f"{user.name}#{user.discriminator}", inline=True)
        embed.add_field(name="ID", value=user.id, inline=True)
        embed.add_field(name="Bot Account", value=user.bot, inline=True)
        embed.add_field(name="Animated Avatar", value=user.is_avatar_animated(), inline=True)
        if member != None:
            account_joined = member.joined_at.strftime("%d-%m-%Y")
            embed.add_field(name="Nickname", value=member.nick, inline=True)
            embed.add_field(name="Top Role", value=member.top_role.name, inline=True)
            embed.add_field(name="Joined At",
                            value=f"{account_joined} ({(ctx.message.created_at - member.joined_at).days} days ago)",
                            inline=True)
        account_made = user.created_at.strftime("%d-%m-%Y")
        embed.add_field(name="Account Created At",
                        value=f"{account_made} ({(ctx.message.created_at - user.created_at).days} days ago)",
                        inline=True)
        embed.add_field(name="Avatar URL", value=user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    async def serverinfo(self, ctx):
        """Shows information about the current server."""
        guild_features = ", ".join(ctx.guild.features)
        print(guild_features)
        if guild_features == "":
            guild_features = None
        role_list = []
        for i in range(len(ctx.guild.roles)):
            role_list.append(ctx.guild.roles[i].name)
        guild_made = ctx.guild.created_at.strftime("%d-%m-%Y")
        embed = discord.Embed(color=0x7289DA)
        embed.set_thumbnail(url=ctx.guild.icon_url)
        requested_at = ctx.message.created_at.strftime("%d-%m-%Y %I:%M%p")
        embed.set_footer(text=f"Requested by {ctx.author.name} at {requested_at}", icon_url=ctx.author.avatar_url)
        embed.add_field(name="Name", value=ctx.guild.name, inline=True)
        embed.add_field(name="ID", value=ctx.guild.id, inline=True)
        embed.add_field(name="Owner", value=ctx.guild.owner, inline=True)
        embed.add_field(name="Members", value=ctx.guild.member_count, inline=True)
        embed.add_field(name="Text Channels", value=len(ctx.guild.text_channels), inline=True)
        embed.add_field(name="Voice Channels", value=len(ctx.guild.voice_channels), inline=True)
        embed.add_field(name="Total Channels", value=len(ctx.guild.text_channels) + len(ctx.guild.voice_channels),
                        inline=True)
        embed.add_field(name="Created at",
                        value=f"{guild_made} ({(ctx.message.created_at - ctx.guild.created_at).days} days ago)",
                        inline=True)
        embed.add_field(name="VIP Features", value=guild_features, inline=True)
        if ctx.guild.icon_url != "":
            embed.add_field(name="Server Icon URL", value=ctx.guild.icon_url, inline=True)
        embed.add_field(name="Roles", value=", ".join(role_list), inline=True)
        await ctx.send(embed=embed)

    async def on_guild_channel_create(self, channel:discord.abc.GuildChannel):
        guild:discord.Guild = channel.guild
        roleid = Configuration.getConfigVar(guild.id, "MUTE_ROLE")
        if roleid is not 0:
            role = discord.utils.get(guild.roles, id=roleid)
            if role is not None and channel.permissions_for(guild.me).manage_channels:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(role, reason="Automatic mute role setup", send_messages=False, add_reactions=False)
                else:
                    await channel.set_permissions(role, reason="Automatic mute role setup", speak=False, connect=False)

    async def on_member_join(self, member: discord.Member):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        if str(member.guild.id) in self.mutes and member.id in self.mutes[str(member.guild.id)]:
            roleid = Configuration.getConfigVar(member.guild.id, "MUTE_ROLE")
            if roleid is not 0:
                role = discord.utils.get(member.guild.roles, id=roleid)
                if role is not None:
                    if member.guild.me.guild_permissions.manage_roles:
                        await member.add_roles(role, reason="Member left and re-joined before mute expired")
                        await GearbotLogging.logToModLog(member.guild, f"<:gearMute:465177981221077003> {member.name}#{member.discriminator} (`{member.id}`) has re-joined the server before his mute expired has has been muted again")
                    else:
                        await GearbotLogging.logToModLog(member.guild, f"{member.name}#{member.discriminator} (`{member.id}`) has re-joined before their mute expired but i am missing the permissions to re-apply the mute")

    async def on_guild_remove(self, guild:discord.Guild):
        if guild.id in self.mutes.keys():
            del self.mutes[guild.id]
            Utils.saveToDisk("mutes", self.mutes)

def setup(bot):
    bot.add_cog(Moderation(bot))

async def unmuteTask(modcog:Moderation):
    while not modcog.bot.STARTUP_COMPLETE:
        await asyncio.sleep(1)
    GearbotLogging.info("Started unmute background task")
    skips = []
    updated = False
    while modcog.running:
        userid = 0
        guildid=0
        try:
            guildstoremove = []
            for guildid, list in modcog.mutes.items():
                guild:discord.Guild = modcog.bot.get_guild(int(guildid))
                toremove = []
                if Configuration.getConfigVar(int(guildid), "MUTE_ROLE") is 0:
                    guildstoremove.append(guildid)
                for userid, until in list.items():
                    if time.time() > until and userid not in skips:
                        member = guild.get_member(int(userid))
                        role = discord.utils.get(guild.roles, id=Configuration.getConfigVar(int(guildid), "MUTE_ROLE"))
                        if guild.me.guild_permissions.manage_roles:
                            await member.remove_roles(role, reason="Mute expired")
                            await GearbotLogging.logToModLog(guild, f"<:gearInnocent:465177981287923712> {member.name}#{member.discriminator} (`{member.id}`) has automaticaly been unmuted")
                        else:
                            await GearbotLogging.logToModLog(guild, f":no_entry: ERROR: {member.name}#{member.discriminator} (`{member.id}`) was muted earlier but I no longer have the permissions needed to unmute this person, please remove the role manually!")
                        updated = True
                        toremove.append(userid)
                for todo in toremove:
                    del list[todo]
                await asyncio.sleep(0)
            if updated:
                Utils.saveToDisk("mutes", modcog.mutes)
                updated = False
            for id in guildstoremove:
                del modcog.mutes[id]
            await asyncio.sleep(10)
        except CancelledError:
            pass #bot shutdown
        except Exception as ex:
            GearbotLogging.error("Something went wrong in the unmute task")
            GearbotLogging.error(traceback.format_exc())
            skips.append(userid)
            embed = discord.Embed(colour=discord.Colour(0xff0000),
                                  timestamp=datetime.datetime.utcfromtimestamp(time.time()))

            embed.set_author(name="Something went wrong in the unmute task:")
            embed.add_field(name="Current guildid", value=guildid)
            embed.add_field(name="Current userid", value=userid)
            embed.add_field(name="Exception", value=ex)
            v = ""
            for line in traceback.format_exc().splitlines():
                if len(v) + len(line) > 1024:
                    embed.add_field(name="Stacktrace", value=v)
                    v = ""
                v = f"{v}\n{line}"
            if len(v) > 0:
                embed.add_field(name="Stacktrace", value=v)
            await GearbotLogging.logToBotlog(embed=embed)
            await asyncio.sleep(10)
    GearbotLogging.info("Unmute background task terminated")
