import asyncio
import random
import re
import time
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import clean_content

from Util import Configuration, Pages, HelpGenerator, Permissioncheckers, Emoji, Translator, Utils, GearbotLogging
from Util.JumboGenerator import JumboGenerator
from database.DatabaseConnector import LoggedMessage, LoggedAttachment

JUMP_LINK_MATCHER = re.compile(r"https://(?:canary|ptb)?\.?discordapp.com/channels/\d*/(\d*)/(\d*)")


class Basic:
    permissions = {
        "min": 0,
        "max": 6,
        "required": 0,
        "commands": {}
    }


    def __init__(self, bot):
        self.bot: commands.Bot = bot
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
                              description=f"{Emoji.get_chat_emoji('DIAMOND')} Gears have been spinning for {days} {'day' if days is 1 else 'days'}, {hours} {'hour' if hours is 1 else 'hours'}, {minutes} {'minute' if minutes is 1 else 'minutes'} and {seconds} {'second' if seconds is 1 else 'seconds'}\n"
                                          f"{Emoji.get_chat_emoji('GOLD')} I received {user_messages} user messages, {bot_messages} bot messages ({self_messages} were mine)\n"
                                          f"{Emoji.get_chat_emoji('IRON')} Number of times people grinded my gears: {self.bot.errors}\n"
                                          f"{Emoji.get_chat_emoji('STONE')} {self.bot.commandCount} commands have been executed, as well as {self.bot.custom_command_count} custom commands\n"
                                          f"{Emoji.get_chat_emoji('WOOD')} Working in {len(self.bot.guilds)} guilds\n"
                                          f"{Emoji.get_chat_emoji('INNOCENT')} With a total of {total} users ({unique} unique)\n"
                                          f":taco: Together they could have eaten {tacos} tacos in this time\n"
                                          f"{Emoji.get_chat_emoji('TODO')} Add more stats")

        embed.add_field(name=f"Support server", value="[Click here](https://discord.gg/vddW3D9)")
        embed.add_field(name=f"Website", value="[Click here](https://gearbot.aenterprise.info)")
        embed.add_field(name=f"Github", value="[Click here](https://github.com/AEnterprise/GearBot)")
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
    async def quote(self, ctx: commands.Context, *, message_info=""):
        """quote_help"""
        message_id = None
        channel_id = None
        if "-" in message_info:
            parts = message_info.split("-")
            if len(parts) is 2:
                try:
                    channel_id = int(parts[0].strip(" "))
                    message_id = int(parts[1].strip(" "))
                except ValueError:
                    pass
        else:
            result = JUMP_LINK_MATCHER.match(message_info)
            if result is not None:
                channel_id = result.group(1)
                message_id = result.group(2)
            else:
                try:
                    message_id = int(message_info)
                except ValueError:
                    pass
        error = None
        dmessage = None
        async with ctx.typing():
            message = LoggedMessage.get_or_none(messageid=message_id)
            if message is None:
                if channel_id is None:
                    for channel in ctx.guild.text_channels:
                        try:
                            permissions = channel.permissions_for(ctx.guild.me)
                            if permissions.read_messages and permissions.read_message_history:
                                dmessage = await channel.get_message(message_id)
                                message = LoggedMessage.create(messageid=message_id, content=dmessage.content,
                                                               author=dmessage.author.id,
                                                               timestamp=dmessage.created_at.timestamp(),
                                                               channel=channel.id, server=dmessage.guild.id)
                                for a in dmessage.attachments:
                                    LoggedAttachment.get_or_create(id=a.id, url=a.url,
                                                                   isImage=(a.width is not None or a.width is 0),
                                                                   messageid=message.id)
                                break
                        except discord.NotFound:
                            pass
                    if message is None:
                        error = Translator.translate('quote_missing_channel', ctx)
                else:
                    channel = self.bot.get_channel(channel_id)
                    if channel is None:
                        error = Translator.translate('quote_invalid_format', ctx)
                    else:
                        try:
                            dmessage: discord.Message = await channel.get_message(message_id)
                        except discord.NotFound as ex:
                            # wrong channel
                            pass
                        else:
                            message = LoggedMessage.create(messageid=message_id, content=dmessage.content,
                                                           author=dmessage.author.id,
                                                           timestamp=dmessage.created_at.timestamp(),
                                                           channel=channel.id, server=dmessage.guild.id)
                            for a in dmessage.attachments:
                                LoggedAttachment.get_or_create(id=a.id, url=a.url,
                                                               isImage=(a.width is not None or a.width is 0),
                                                               messageid=message.id)

            if message is not None:
                channel = self.bot.get_channel(message.channel)
                # validate message still exists
                if dmessage is None:
                    try:
                        dmessage = await channel.get_message(message_id)
                    except discord.NotFound:
                        error = Translator.translate("quote_not_found", ctx)
                if dmessage is not None:
                    # validate user is allowed to quote
                    member = channel.guild.get_member(ctx.author.id)
                    if member is None:
                        error = Translator.translate("quote_not_visible_to_user", ctx)
                    else:
                        permissions = channel.permissions_for(member)
                        if not (permissions.read_message_history and permissions.read_message_history):
                            error = Translator.translate("quote_not_visible_to_user", ctx)
            elif error is None:
                error = Translator.translate("quote_not_found", ctx)

        if error is None:
            if channel.is_nsfw() and not ctx.channel.is_nsfw():
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('quote_nsfw_refused', ctx)}")
            else:
                attachment = None
                attachments = LoggedAttachment.select().where(LoggedAttachment.messageid == message_id)
                if len(attachments) == 1:
                    attachment = attachments[0]
                embed = discord.Embed(colour=discord.Color(0xd5fff),
                                      timestamp=datetime.utcfromtimestamp(message.timestamp))
                if message.content is None or message.content == "":
                    if attachment is not None:
                        if attachment.isImage:
                            embed.set_image(url=attachment.url)
                        else:
                            embed.add_field(name=Translator.translate("attachment_link", ctx), value=attachment.url)
                else:
                    description = message.content
                    embed = discord.Embed(colour=discord.Color(0xd5fff), description=description,
                                          timestamp=datetime.utcfromtimestamp(message.timestamp))
                    embed.add_field(name="​",
                                    value=f"https://discordapp.com/channels/{channel.guild.id}/{channel.id}/{message_id}")
                    if attachment is not None:
                        if attachment.isImage:
                            embed.set_image(url=attachment.url)
                        else:
                            embed.add_field(name=Translator.translate("attachment_link", ctx), value=attachment.url)
                user = channel.guild.get_member(message.author)
                if user is None:
                    user = await ctx.bot.get_user_info(message.author)
                embed.set_author(name=user.name, icon_url=user.avatar_url)
                embed.set_footer(
                    text=Translator.translate("quote_footer", ctx, channel=self.bot.get_channel(message.channel).name,
                                              user=Utils.clean(ctx.author.display_name), message_id=message_id))
                await ctx.send(embed=embed)
                if ctx.channel.permissions_for(ctx.me).manage_messages:
                    await ctx.message.delete()
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {error}")

    @commands.command()
    async def coinflip(self, ctx, *, thing: str = ""):
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
            title=Translator.translate("assignable_roles", ctx, server_name=ctx.guild.name, page_num=page_num + 1,
                                       page_count=len(pages)), color=0x54d5ff, description=page)
        return None, embed, page_num

    def gen_role_pages(self, guild: discord.Guild):
        roles = Configuration.getConfigVar(guild.id, "SELF_ROLES")
        current_roles = ""
        count = 1
        for role in roles:
            current_roles += f"{count}) <@&{role}>\n\n"
            count += 1
            if count > 10:
                count = 1
        return Pages.paginate(current_roles, max_lines=20)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def role(self, ctx: commands.Context, *, role: str = None):
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
                    try:
                        if role in ctx.author.roles:
                            await ctx.author.remove_roles(role)
                            await ctx.send(Translator.translate("role_left", ctx, role_name=role.name))
                        else:
                            await ctx.author.add_roles(role)
                            await ctx.send(Translator.translate("role_joined", ctx, role_name=role.name))
                    except discord.Forbidden:
                        await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mute_role_to_high', ctx, role=role.name)}")
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
                "help_not_found" if len(query) < 1500 else "help_no_wall_allowed", ctx, query=query_clean)), None, False, []
        return f"**{Translator.translate('help_title', ctx, page_num=1, pages=len(pages))}**```diff\n{pages[0]}```", None, len(
            pages) > 1, []

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

    @commands.command()
    async def jumbo(self, ctx, *, emojis: str):
        """Jumbo emoji"""
        # try:
        #     await asyncio.wait_for(self._jumbo(ctx, emojis), timeout=60)
        # except asyncio.TimeoutError:
        #     await ctx.send(f"{Emoji.get_chat_emoji('WHAT')} {Translator.translate('jumbo_timeout', ctx)}")
        await JumboGenerator(ctx, emojis).generate()





    async def on_guild_role_delete(self, role: discord.Role):
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

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        if guild.me.id == payload.user_id:
            return
        try:
            message = await self.bot.get_channel(payload.channel_id).get_message(payload.message_id)
        except discord.NotFound:
            pass
        else:
            if str(payload.message_id) in Pages.known_messages:
                info = Pages.known_messages[str(payload.message_id)]
                if info["type"] == "role":
                    for i in range(10):
                        e = Emoji.get_emoji(str(i + 1))
                        if payload.emoji.name == e:
                            roles = Configuration.getConfigVar(guild.id, "SELF_ROLES")
                            role = discord.utils.get(guild.roles, id=roles[info['page'] * 10 + i])
                            member = guild.get_member(payload.user_id)
                            channel = self.bot.get_channel(payload.channel_id)
                            try:
                                if role in member.roles:
                                    await member.remove_roles(role)
                                    await channel.send(f"{member.mention} {Translator.translate('role_left', payload.guild_id, role_name=role.name)}", delete_after=10)
                                else:
                                    await member.add_roles(role)
                                    await channel.send(f"{member.mention} {Translator.translate('role_joined', payload.guild_id, role_name=role.name)}", delete_after=10)
                            except discord.Forbidden:
                                await channel.send(
                                    f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mute_role_to_high', payload.guild_id, role=role.name)}")
                            if channel.permissions_for(guild.me).manage_messages:
                                await message.remove_reaction(e, member)
                            break


def setup(bot):
    bot.add_cog(Basic(bot))
