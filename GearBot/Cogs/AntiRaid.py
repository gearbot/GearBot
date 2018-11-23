import asyncio
import os
import time
from collections import deque
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import MemberConverter, BadArgument, Greedy

from Util import Utils, Confirmation, Configuration, GearbotLogging
from Util.Converters import PotentialID, Reason, RaidInfo


class AntiRaid:
    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.trackers = dict()
        self.under_raid = dict()
        self.bad_names = []
        self.load_bad_names()
        self.kick_trackers = dict()
        self.raid_timeout = 120
        # all raid info
        if not os.path.isdir("raids"):
            os.mkdir("raids")
            with open("raids/counter", "w") as file:
                file.write("0")

        # load last raid id
        with open("raids/counter") as file:
            self.last_raid = int(file.read())

    async def __local_check(self, ctx):
        return ctx.author.guild_permissions.ban_members

    def load_bad_names(self):
        if os.path.isfile("bad_names.txt"):
            with open("bad_names.txt", encoding="UTF-8") as namefile:
                self.bad_names = [line.rstrip().strip() for line in namefile.readlines()]
        else:
            with open("bad_names.txt", "w", encoding="UTF-8") as namefile:
                namefile.write(
                    "PLEASE REMOVE THIS LINE AND PUT ALL NAMES TO KICK UPON JOINING HERE, ONE NAME PER LINE, CASE INSENSITIVE")

    @staticmethod
    def _can_act(ctx, user: discord.Member):
        if (ctx.author != user and user != ctx.bot.user and ctx.author.top_role > user.top_role) or \
                (ctx.guild.owner == ctx.author and ctx.author != user):
            if ctx.me.top_role > user.top_role:
                return True, None
            else:
                return False, f"Unable to ban {user} as I do not have a higher role than them."
        else:
            return False, f"You are not allowed to ban {user}."

    @commands.guild_only()
    @commands.command()
    @commands.bot_has_permissions(ban_members=True)
    async def mban(self, ctx, targets: Greedy[PotentialID], *, reason: Reason = ""):
        """mban_help"""
        if reason == "":
            reason = "No reason specified"

        async def yes():
            pmessage = await ctx.send("🔁 Processing")
            valid = 0
            failures = []
            for t in targets:
                try:
                    member = await MemberConverter().convert(ctx, str(t))
                except BadArgument:
                    user = discord.Object(t)
                    try:
                        await ctx.guild.ban(user,
                                            reason=f"Moderator: {ctx.author.name} ({ctx.author.id}) Reason: {reason}",
                                            delete_message_days=0)
                    except discord.NotFound as bad:
                        failures.append(f"``{t}``: Unable to convert to a user")
                    else:

                        valid += 1
                else:
                    allowed, message = self._can_act(ctx, member)
                    if allowed:
                        await ctx.guild.ban(member,
                                            reason=f"Moderator: {ctx.author.name} ({ctx.author.id}) Reason: {reason}",
                                            delete_message_days=0)
                        valid += 1
                    else:
                        failures.append(f"``{t}``: {message}")
            await pmessage.delete()
            await ctx.send(f"✅ Successfully banned {valid} people.")
            if len(failures) > 0:
                test = "\n"
                for page in Utils.paginate(f"🚫 I failed to ban the following users:\n{test.join(failures)}"):
                    await ctx.send(page)

        await Confirmation.confirm(ctx, "Are you sure you want to ban all those people?", on_yes=yes)

    async def on_member_join(self, member: discord.Member):
        self.bot.loop.create_task(self._track(member))
        await self.check_name(member)

    async def _track(self, member):
        # grab the tracker
        guild_id = member.guild.id
        if guild_id not in self.trackers:
            self.trackers[guild_id] = set()

        tracker = self.trackers[guild_id]

        # start tracking
        tracker.add(member)

        # is there a raid going on?
        if guild_id in self.under_raid:
            await self._handle_raider(member)
        else:
            # do we have 5 people who in the last 3 seconds or 10 in 60 maybe??
            now = datetime.utcfromtimestamp(time.time())
            if len(tracker) >= 5 and (now - tracker[-5].joined_at).seconds <= 30 or \
                    len(tracker) >= 10 and (now - tracker[-10].joined_at).seconds <= 60:
                await self._sound_the_alarm(member.guild)

        await asyncio.sleep(60)

        # don't release anyone until the raid is over
        while guild_id in self.under_raid:
            await asyncio.sleep(1)
        tracker.remove(member)

    async def _handle_raider(self, member):
        guild_id = member.guild.id
        raid_info = self.under_raid[guild_id]
        channel = self._get_mod_channel(member.guild.id)
        if channel is not None and len(raid_info["TODO"]) is 0:
            if len(raid_info["RAIDERS"]) > 0:
                await channel.send("New raid group detected!")
            raid_info["MESSAGE"] = await self.send_dash(channel, self.under_raid[guild_id])
        raid_info["RAIDERS"][str(member.id)] = {
            "user_name": str(member),
            "joined_at": str(member.joined_at),
            "state": "muted"
        }
        raid_info["TODO"].append(member.id)
        raid_info["LAST_JOIN"] = member.joined_at
        await self.mute(member)

    async def _sound_the_alarm(self, guild):
        Logging.info(f"Sounding the alarm for {guild} ({guild.id})!")
        guild_id = guild.id

        # apply alarm, grab id later reference
        raid_id = self.last_raid = self.last_raid + 1
        with open("raids/counter", "w") as file:
            file.write(str(raid_id))
            now = datetime.utcfromtimestamp(time.time())
        self.under_raid[guild_id] = {
            "ID": raid_id,
            "GUILD": guild_id,
            "RAIDERS": {},
            "MESSAGE": None,
            "TODO": [],
            "LAST_JOIN": now,
            "DETECTED": str(now),
            "ENDED": "NOT YET"
        }

        channel = self.bot.get_channel(Configuration.get_var(guild_id, f"MOD_CHANNEL"))
        if channel is not None:
            await channel.send(Configuration.get_var(guild_id, f"RAID_ALARM_MESSAGE"))

        else:
            Logging.warn(f"Unable to sound the alarm in {guild.name} ({guild_id})")
            await guild.owner.send(
                f"🚨 Anti-raid alarm triggered for {guild.name} but the mod channel is misconfigured, please use ``!status`` somewhere in that server to get the raid status 🚨")

        # deal with current raiders
        for raider in self.trackers[guild.id]:
            await self._handle_raider(raider)

        self.bot.loop.create_task(self._alarm_checker(guild))

    async def _alarm_checker(self, guild):
        guild_id = guild.id
        tracker = self.trackers[guild_id]
        while guild_id in self.under_raid:
            now = datetime.utcfromtimestamp(time.time())
            # lift alarm when there are no new joins for 2 mins
            if (now - tracker[-1].joined_at).seconds >= self.raid_timeout:
                await self._terminate_raid(guild)
            else:
                await self._update_status(guild_id)
                await asyncio.sleep(2)

    async def _terminate_raid(self, guild):
        guild_id = guild.id
        raid_info = self.under_raid[guild_id]
        raid_info["ENDED"] = str(datetime.utcfromtimestamp(time.time()))
        self._save_raid(raid_info)
        Logging.info(f"Lifted alarm in {guild}")
        del self.under_raid[guild_id]
        channel = self._get_mod_channel(guild_id)
        if channel is not None:
            total = len(raid_info['RAIDERS'])
            left = len(raid_info["TODO"])
            handled = total - left
            await channel.send(
                f"Raid party is over :( Guess i'm done handing out special roles (for now).\n**Summary:**\nRaid ID: {raid_info['ID']}\n{total} guests showed up for the party\n{left} are still hanging out, enjoying that oh so special role they got\n{handled} are no longer with us.")

    @staticmethod
    def _save_raid(raid_info):
        Utils.save_to_disk(f"raids/{raid_info['ID']}",
                           {k: v for k, v in raid_info.items() if k not in ["MESSAGE", "TODO", "LAST_JOIN"]})

    async def _update_status(self, guild):
        raid_info = self.under_raid[guild]
        if raid_info["MESSAGE"] is not None:
            await raid_info["MESSAGE"].edit(content=self._get_message(raid_info))

    async def send_dash(self, channel, raid_info):
        message = await channel.send(self._get_message(raid_info))
        raid_info["MESSAGE"] = message
        await message.add_reaction("🚪")
        await message.add_reaction("👢")
        await message.add_reaction("✖")
        return message

    def _get_message(self, raid_info):
        # assemble current status
        total = len(raid_info['RAIDERS'])
        current = len(raid_info['TODO'])
        past = total - current
        now = datetime.utcfromtimestamp(time.time())
        remaining = self.raid_timeout - (now - raid_info["LAST_JOIN"]).seconds
        return f"Total raiders: {total}\nRaiders already handled: {past}\nRaiders locked in for mod actions: {current}\nTime until alarm reset: {remaining} seconds"

    async def mute(self, member):
        role = member.guild.get_role(Configuration.get_var(member.guild.id, "MUTE_ROLE"))
        if role is not None:
            try:
                await member.add_roles(role, reason="Raid alarm triggered")
            except discord.HTTPException:
                Logging.warn(f"failed to mute {member} ({member.id}!")

    async def on_member_update(self, before, after):
        if before.nick != after.nick or before.name != after.name:
            await self.check_name(after)

    async def check_name(self, member):
        if member.nick is not None:
            nick = member.nick.lower()
            if any(bad in nick for bad in self.bad_names):
                await member.edit(nick="Squeaky clean")
        name = member.name.lower()
        if any(bad in name for bad in self.bad_names):
            for guild in self.bot.guilds:
                real_member = guild.get_member(member.id)
                if real_member is not None:
                    channel = self.bot.get_channel(Configuration.get_var(guild.id, "ACTION_CHANNEL"))

                    # track selfbots and others who don't get the hint
                    if guild.id not in self.kick_trackers:
                        self.kick_trackers[guild.id] = deque(maxlen=10)
                    tracker = self.kick_trackers[guild.id]
                    tracker.append(member.id)
                    # boot them out, grab the hammer if they don't get the hint (or use auto-joining self-bot)
                    if tracker.count(member.id) >= 5:
                        await real_member.ban(Reason="Too many bad names, didn't get the hint")
                        message = f"Banned {member} ({member.id}) as they kept returning with a bad name"
                    else:
                        await real_member.kick(reason="Bad username")
                        message = f"Kicked {member} (``{member.id}``) for having a bad username"
                    if channel is not None:
                        await channel.send(message)




    @commands.command()
    async def status(self, ctx):
        if ctx.guild.id in self.under_raid:
            await ctx.send(
                "This server is being raided, everyone who joins now gets a special role and thrown into the report pool! :D")
            await self.send_dash(ctx, self.under_raid[ctx.guild.id])
        else:
            await ctx.send("I'm bored, there is no raid going on atm :(")

    async def ban_all_raiders(self, channel, raid_info):
        # turn into objects just in case some left already so we can't fail that way and store in new list
        # so we don't get concurrent modification issues if new people join
        targets = [discord.Object(m) for m in raid_info["TODO"]]
        raid_info["TODO"] = []
        failures = []
        message = await channel.send("Showing raiders the door...")
        for target in targets:
            try:
                await channel.guild.ban(target, reason=f"Raid cleanup, raid ID: {raid_info['ID']}")
                raid_info["RAIDERS"][str(target.id)]["state"] = "banned"
            except discord.DiscordException as ex:
                failures.append(str(target.id))
        await message.edit(
            content=f"Banned {len(targets) - len(failures)} raiders\nFailed to ban {len(failures)} raiders")
        if len(failures) > 0:
            test = '\n'
            for page in Utils.paginate(f"🚫 I failed to ban the following users:\n{test.join(failures)}"):
                await channel.send(page)

    async def kick_all_raiders(self, channel, raid_info):
        # grab just IDs so we can grab the members to check if they are even still here
        targets = [m for m in raid_info["TODO"]]
        raid_info["TODO"] = []
        failures = []
        left = 0
        message = await channel.send("Grabbing my boots...")
        for target in targets:
            try:
                member = channel.guild.get_member(target)
                if member is not None:
                    await member.kick(reason=f"Raid cleanup, raid ID: {raid_info['ID']}")
                    raid_info["RAIDERS"][str(target)]["state"] = "Kicked"
                else:
                    left += 1
            except discord.HTTPException:
                failures.append(str(target))
        await message.edit(
            content=f"Kicked {len(targets) - len(failures)} raiders\nFailed to boot {len(failures)} raiders\n{left} Already left")
        if len(failures) > 0:
            test = '\n'
            for page in Utils.paginate(f"🚫 I failed to kick the following users:\n{test.join(failures)}"):
                await channel.send(page)

    async def dismiss_raid(self, channel, raid_info):
        await channel.send("That wasn't a raid? Sorry about that, turning off the alarms")
        targets = [m for m in raid_info["TODO"]]
        failures = []
        # terminate raid
        if channel.guild.id in self.under_raid:
            await self._terminate_raid(channel.guild)
        message = await channel.send("Unmuting people...")
        # remove mute role from people who have been detected
        for target in targets:
            member = channel.guild.get_member(target)
            if member is not None:
                role = member.guild.get_role(Configuration.get_var(member.guild.id, "MUTE_ROLE"))
                if role is not None:
                    try:
                        await member.remove_roles(role, reason="Raid alarm dismissed")
                        raid_info['RAIDERS'][str(target)]["state"] = "Dismissed"
                    except discord.HTTPException:
                        failures.append(str(target))
        await channel.send(f"{len(targets) - len(failures)} have been unmuted")
        if len(failures) > 0:
            people = '\n'.join(failures)
            out = f"Failed to unmute the following people:\n{people}"
            for page in Utils.paginate(out):
                await channel.send(page)

    @commands.group("raid_info")
    async def raid_info(self, ctx):
        if ctx.invoked_subcommand == self.raid_info:
            await ctx.send("Base command for getting raid info, pls use one of the subcommands: 'raw', 'ids', 'pretty'")

    @raid_info.command("raw")
    async def raid_info_raw(self, ctx, raid_info: RaidInfo):
        raid_id = raid_info["ID"]
        with open(f"raids/{raid_id}.json", "rb") as file:
            await ctx.send(f"Raw raid data for raid {raid_id}:", file=discord.File(file, f"raid_{raid_id}.json"))

    @raid_info.command("ids")
    async def raid_info_ids(self, ctx, raid_info: RaidInfo):
        # just print out the ids
        raid_id = raid_info["ID"]
        ids = ' '.join(raid_info["RAIDERS"].keys())
        message = f"User IDs of all users associated with raid {raid_id}:\n{ids}"
        for page in Utils.paginate(message):
            await ctx.send(page)

    @raid_info.command("pretty")
    async def raid_info_pretty(self, ctx, raid_info: RaidInfo):
        # get longest name to keep things pretty
        lengths = [len(info["user_name"]) for info in raid_info["RAIDERS"].values()]
        lengths.append(20)
        longest_name = max(lengths)
        # pretty header with line
        header = f"ID {' ' * 18}| Name (at that time) {' ' * (longest_name - 19)}| Joined at                  | Action taken\n"
        text = f"{header}{'-' * len(header)} \n"
        # add all raiders
        for id, info in raid_info["RAIDERS"].items():
            text += f"{Utils.pad(id, 20)} | {Utils.pad(info['user_name'], longest_name)} | {info['joined_at']} | {info['state']}\n"
        # send all ot the printer in codeblocks
        pages = Utils.paginate(text, prefix="```", suffix="```")
        for page in pages:
            await ctx.send(page)

    @commands.group()
    async def inf(self, ctx):
        pass

    @inf.command()
    async def search(self, ctx, query: str = None):
        if query is None:
            return
        # rowboat has no clue about outboard actions, so we just print them ourselves when people search
        try:
            # just try to parse, it, don't care about what it is, we need the string to lookup anyways
            int(query)
        except ValueError:
            # not an id, not our problem, just stay silent
            pass
        else:
            # check all past raids for involvement, only reply if we find something for this guild
            directory = os.fsencode("raids")
            for file in os.listdir(directory):
                filename = os.fsdecode(file)
                if filename.endswith(".json"):
                    raid_data = Utils.fetch_from_disk(f"raids/{filename}", "")
                    if raid_data["GUILD"] == ctx.guild.id:
                        if query in raid_data["RAIDERS"]:
                            info = raid_data['RAIDERS'][query]
                            await ctx.send(
                                f"{query} was involved in raid {raid_data['ID']} under the name {info['user_name']} and has been {info['state']} for it")
                    # cycle the loop just in case so we don't start timing out if we have to process a lot of raids
                    await asyncio.sleep(0)

    @commands.group()
    async def raid_act(self, ctx):
        if ctx.invoked_subcommand == self.raid_act:
            await ctx.send("Please use the subcommands: 'ban', 'kick' or 'dismiss'")

    @raid_act.command("ban")
    async def raid_act_ban(self, ctx, raid_info: RaidInfo):
        async def yes():
            # targeting all raiders
            raid_info["TODO"] = [int(id) for id in raid_info["RAIDERS"].keys()]
            await self.ban_all_raiders(ctx.channel, raid_info)
            self._save_raid(raid_info)

        await Confirmation.confirm(ctx,
                                   f"Are you sure you want to ban all {len(raid_info['RAIDERS'])} raiders involved in raid {raid_info['ID']} ?",
                                   on_yes=yes)

    @raid_act.command("kick")
    async def raid_act_kick(self, ctx, raid_info: RaidInfo):
        async def yes():
            # targeting all raiders
            raid_info["TODO"] = [int(id) for id in raid_info["RAIDERS"].keys()]
            await self.kick_all_raiders(ctx.channel, raid_info)
            self._save_raid(raid_info)

        await Confirmation.confirm(ctx,
                                   f"Are you sure you want to kick all {len(raid_info['RAIDERS'])} raiders involved in raid {raid_info['ID']} ?",
                                   on_yes=yes)

    @raid_act.command("dismiss")
    async def raid_act_dismiss(self, ctx, raid_info: RaidInfo):
        async def yes():
            # targeting all raiders
            raid_info["TODO"] = [int(id) for id in raid_info["RAIDERS"].keys()]
            await self.dismiss_raid(ctx.channel, raid_info)
            self._save_raid(raid_info)

        await Confirmation.confirm(ctx,
                                   f"Are you sure you want to dismiss raid {raid_info['ID']} and unmute all {len(raid_info['RAIDERS'])} raiders ?",
                                   on_yes=yes)

    def _get_mod_channel(self, guild):
        return self.bot.get_channel(Configuration.get_var(guild, f"MOD_CHANNEL"))

    async def on_reaction_add(self, reaction, user):
        responses = {
            "🚪": self.ban_all_raiders,
            "👢": self.kick_all_raiders,
            "✖": self.dismiss_raid
        }
        guild_id = reaction.message.guild.id
        if guild_id in self.under_raid:
            raid_info = self.under_raid[guild_id]
            raid_message = raid_info["MESSAGE"]
            if reaction.message.id == raid_message.id and user.id != self.bot.user.id:
                if reaction.emoji in responses:
                    raid_info["MESSAGE"] = None
                    await responses[reaction.emoji](reaction.message.channel, raid_info)


def setup(bot):
    bot.add_cog(Moderation(bot))
