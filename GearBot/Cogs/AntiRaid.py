import asyncio
import time
from datetime import datetime

import discord

from Bot.GearBot import GearBot
from Util import Configuration, GearbotLogging, MessageUtils
from Util.RaidHandling.RaidShield import RaidShield
from database.DatabaseConnector import Raid, Raider


class AntiRaid:
    def __init__(self, bot):
        self.bot: GearBot = bot
        self.raid_trackers = dict()
        self.timers = {
            "fixed": self.fixed_time,
            "resetting": self.resetting
        }

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

        #cleaning pipe!
        pipeline = self.bot.redis_pool.pipeline()

        now = datetime.utcfromtimestamp(time.time())
        for user in potential_raiders:
            m = member.guild.get_member(int(user))
            #discard users who are no left already
            if m is None:
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
            #check if it's not disabled
            if not shield["enabled"]:
                continue

            # check if active, if it is, let that take care of it
            if member.guild.id in self.raid_trackers and shield["id"] in self.raid_trackers[member.guild.id]["SHIELDS"]:
                for _, h in self.raid_trackers[member.guild.id]["SHIELDS"]:
                    Raider.create(raid=self.raid_trackers[member.guild.id]["raid_id"], user_id=member.id, joined_at=member.joined_at)
                    self.raid_trackers[member.guild.id]["raider_ids"][member.id] = Raider.id
                    await h.handle_raider(self.bot, member, self.raid_trackers[member.guild.id]["id"], self.raid_trackers[member.guild.id]["raider_ids"])
                continue

            #not active, check if we should trigger
            trigger_info = shield["trigger"]


            if len(buckets[shield["id"]]) >= trigger_info["count"] and (member.guild.id not in self.raid_trackers and shield["id"] or shield["id"] not in self.raid_trackers[member.guild.id]["triggered"]):
                #TRIGGERED
                # assign raid id, track raiders
                raid = Raid.create(guild_id=member.guild.id, start=datetime.utcfromtimestamp(time.time()))
                GearbotLogging.log_to(member.guild.id, "RAID_LOGS", MessageUtils.assemble(member.guild.id, 'BAD_USER', 'raid_new', raid_id=raid.id))

                # create trackers if needed
                if member.guild.id not in self.raid_trackers:
                    raider_ids = dict()
                    for raider in buckets[shield["id"]]:
                        Raider.create(raid=raid, user_id=raider.id, joined_at=raider.joined_at)
                        raider_ids[member.id] = Raider.id

                    self.raid_trackers[member.guild.id] = dict(raid_id=raid.id, SHIELDS=dict(), raider_ids=raider_ids, triggered=set())

                #assign the handler and call execute initial actions
                h = RaidShield(shield)
                self.raid_trackers[member.guild.id]["SHIELDS"][shield["id"]] = h
                self.raid_trackers[member.guild.id]["triggered"].add(shield["id"])
                await h.raid_detected(self.bot, member.guild, raid.id, self.raid_trackers[member.guild.id]["raider_ids"], shield)

                # create background terminator
                self.bot.loop.create_task(
                    self.timers[shield["duration"]["type"]](member.guild.id, h, shield, shield["duration"]))

                # deal with them
                for raider in buckets[shield["id"]]:
                    await h.handle_raider(self.bot, raider, raid.id, self.raid_trackers[member.guild.id]["raider_ids"], shield)



    async def fixed_time(self, guild_id, handler, shield, data):
        await asyncio.sleep(data["time"])
        await self.terminate_shield(guild_id, handler, shield)


    async def resetting(self, guild_id, handler, shield, data):
        while True:
            try:
                self.bot.wait_for("member_add", check=lambda m: m.guild.id == guild_id, timeout=data["duration"])
            except asyncio.TimeoutError:
                # no more joins! turn off the handler
                await self.terminate_shield(guild_id, handler, shield)
                pass # timer reset!


    async def terminate_shield(self, guild_id, handler, shield):
        del self.raid_trackers[guild_id]["SHIELDS"][shield["id"]]
        await handler.shield_terminated(self.bot, self.bot.get_guild(guild_id), self.raid_trackers[guild_id]["raid_id"], self.raid_trackers[guild_id]["raider_ids"], shield)
        if len(self.raid_trackers[guild_id]["SHIELDS"]) == 0:
            GearbotLogging.log_to(guild_id, "RAID_LOGS", MessageUtils.assemble(guild_id, "INNOCENT", 'raid_terminated',
                                                                  raid_id=self.raid_trackers[guild_id]['raid_id']))
            del self.raid_trackers[guild_id]









def setup(bot):
    bot.add_cog(AntiRaid(bot))
