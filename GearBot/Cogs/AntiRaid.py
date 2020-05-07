import asyncio
import time
from datetime import datetime

import discord
from discord.ext import commands

from Cogs.BaseCog import BaseCog
from Util import Configuration, GearbotLogging, MessageUtils
from Util.RaidHandling.RaidShield import RaidShield
from database.DatabaseConnector import Raid, Raider


class AntiRaid(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)

        self.raid_trackers = dict()
        self.timers = {
            "fixed": self.fixed_time,
            "resetting": self.resetting
        }

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        raid_settings = Configuration.get_var(member.guild.id, "RAID_HANDLING")
        if not raid_settings["ENABLED"]:
            return

        # track in redis, pipelines reduce overhead of multiple commands
        pipeline = self.bot.redis_pool.pipeline()
        key = f"joins:{member.guild.id}"
        pipeline.sadd(key, member.id)

        # get all potential raiders
        pipeline.smembers(key)
        _, potential_raiders = await pipeline.execute()

        longest = max(h["trigger"]["seconds"] for h in raid_settings["SHIELDS"])
        buckets = {h["id"]: [] for h in raid_settings["SHIELDS"]}

        # cleaning pipe!
        pipeline = self.bot.redis_pool.pipeline()

        now = datetime.utcfromtimestamp(time.time())
        for user in potential_raiders:
            m = member.guild.get_member(int(user))
            # discard users who are no left already
            if m is None:
                pipeline.srem(key, user)
                continue
            if m.joined_at is None:
                GearbotLogging.warn(f"User {m.id} in {m.guild.id} has no joined timestamp, disregarding")
                pipeline.srem(key, user)
                continue
            dif = abs((now - m.joined_at).total_seconds())
            # clean up users who have been here for long enough
            if dif >= longest:
                pipeline.srem(key, user)
            else:
                # put them in the buckets
                for h in raid_settings["SHIELDS"]:
                    if dif < h["trigger"]["seconds"]:
                        buckets[h["id"]].append(m)

        # clean up now? you crazy, i'll do it later!
        self.bot.loop.create_task(pipeline.execute())

        # stored, fetched and sorted them, now to take care of the bad guys
        for shield in raid_settings["SHIELDS"]:
            # check if it's not disabled
            if not shield["enabled"]:
                continue

            # check if active, if it is, let that take care of it
            if member.guild.id in self.raid_trackers and shield["id"] in self.raid_trackers[member.guild.id]["SHIELDS"]:
                h = self.raid_trackers[member.guild.id]["SHIELDS"][shield["id"]]
                if member.id not in self.raid_trackers[member.guild.id]["raider_ids"]:
                    r = await Raider.create(raid=self.raid_trackers[member.guild.id]["raid"], user_id=member.id,
                                            joined_at=member.joined_at.timestamp())
                    self.raid_trackers[member.guild.id]["raider_ids"][member.id] = r.id
                await h.handle_raider(self.bot, member, self.raid_trackers[member.guild.id]["raid_id"],
                                      self.raid_trackers[member.guild.id]["raider_ids"], shield)
                continue

            # not active, check if we should trigger
            trigger_info = shield["trigger"]

            if len(buckets[shield["id"]]) >= trigger_info["count"] and (
                    member.guild.id not in self.raid_trackers or shield["id"] not in
                    self.raid_trackers[member.guild.id]["triggered"]):
                # TRIGGERED
                if member.guild.id not in self.raid_trackers:
                    # assign raid id, track raiders
                    raid = await Raid.create(guild_id=member.guild.id, start=time.time())
                    GearbotLogging.log_key(member.guild.id, 'raid_new', raid_id=raid.id)
                    # create trackers if needed
                    raider_ids = dict()
                    terminator = self.bot.loop.create_task(self.terminator(member.guild.id))
                    self.raid_trackers[member.guild.id] = dict(raid_id=raid.id, SHIELDS=dict(), raider_ids=raider_ids,
                                                               triggered=set(), terminator=terminator, timers=[], raid=raid)
                    for raider in buckets[shield["id"]]:
                        if member.guild.id not in self.raid_trackers or member.id not in \
                                self.raid_trackers[member.guild.id]["raider_ids"]:
                            r = await Raider.create(raid=raid, user_id=raider.id, joined_at=raider.joined_at.timestamp())
                            raider_ids[member.id] = r.id

                # assign the handler and call execute initial actions
                h = RaidShield(shield)
                self.raid_trackers[member.guild.id]["SHIELDS"][shield["id"]] = h
                self.raid_trackers[member.guild.id]["triggered"].add(shield["id"])
                await h.raid_detected(self.bot, member.guild, self.raid_trackers[member.guild.id]["raid_id"],
                                      self.raid_trackers[member.guild.id]["raider_ids"], shield)

                # create background terminator
                timer = self.bot.loop.create_task(
                    self.timers[shield["duration"]["type"]](member.guild.id, h, shield, shield["duration"]))
                self.raid_trackers[member.guild.id]["timers"].append(timer)

                # deal with them
                for raider in buckets[shield["id"]]:
                    await h.handle_raider(self.bot, raider, self.raid_trackers[member.guild.id]["raid_id"],
                                          self.raid_trackers[member.guild.id]["raider_ids"], shield)

    async def terminator(self, guild_id):
        await asyncio.sleep(10 * 60)
        if guild_id in self.raid_trackers:
            GearbotLogging.log_key(guild_id, "raid_timelimit_exceeded")
            info = self.raid_trackers[guild_id]
            del self.raid_trackers[self.raid_trackers]
            for t in info["timers"]:
                t.cancel()

    async def fixed_time(self, guild_id, handler, shield, data):
        await asyncio.sleep(data["time"])
        await self.terminate_shield(guild_id, handler, shield)

    async def resetting(self, guild_id, handler, shield, data):
        initialized_at = datetime.utcfromtimestamp(time.time())
        while True:
            try:
                await self.bot.wait_for("member_add", check=lambda m: m.guild.id == guild_id, timeout=data["time"])
                diff = abs((datetime.utcfromtimestamp(time.time()) - initialized_at).total_seconds())
                if diff > 15 * 60:
                    GearbotLogging.log_key(guild_id, 'shield_time_limit_reached', shield_name=shield["name"])
                    await self.terminate_shield(guild_id, handler, shield)
                    return
            except asyncio.TimeoutError:
                # no more joins! turn off the handler
                if abs((datetime.utcfromtimestamp(time.time()) - initialized_at).total_seconds()) >= shield["trigger"][
                    "seconds"]:
                    await self.terminate_shield(guild_id, handler, shield)
                    return  # don't leak tasks

    async def terminate_shield(self, guild_id, handler, shield):
        del self.raid_trackers[guild_id]["SHIELDS"][shield["id"]]
        await handler.shield_terminated(self.bot, self.bot.get_guild(guild_id), self.raid_trackers[guild_id]["raid_id"],
                                        self.raid_trackers[guild_id]["raider_ids"], shield)
        if len(self.raid_trackers[guild_id]["SHIELDS"]) == 0:
            GearbotLogging.log_key(guild_id, 'raid_terminated', raid_id=self.raid_trackers[guild_id]['raid_id'])
            self.raid_trackers[guild_id]["terminator"].cancel()
            del self.raid_trackers[guild_id]

    @commands.group()
    async def raid(self, ctx):
        pass

    @raid.command("end")
    async def raid_end(self, ctx):
        if ctx.guild.id not in self.raid_trackers:
            await MessageUtils.send_to(ctx, 'WHAT', "raid_terminate_no_raid")
        else:
            await self.terminate_raid(ctx.guild.id)
            await MessageUtils.send_to(ctx, 'YES', 'raid_terminated')

    async def terminate_raid(self, guild):
        raid_settings = Configuration.get_var(guild, "RAID_HANDLING")
        for shield in raid_settings["SHIELDS"]:
            if guild in self.raid_trackers and shield["id"] in self.raid_trackers[guild]["SHIELDS"]:
                h = self.raid_trackers[guild]["SHIELDS"][shield["id"]]
                await self.terminate_shield(guild, h, shield)


def setup(bot):
    bot.add_cog(AntiRaid(bot))
