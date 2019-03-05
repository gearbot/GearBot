import asyncio
import time
from datetime import datetime

import discord

from Bot.GearBot import GearBot
from Util import Configuration, GearbotLogging, MessageUtils
from Util.RaidHandling.RaidHandler import RaidHandler
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
        if not raid_settings["enabled"]:
            return


        # track in redis, pipelines reduce overhead of multiple commands
        pipeline = self.bot.redis_pool.pipeline()
        key = f"joins:{member.guild.id}"
        pipeline.sadd(key, member.id)

        # get all potential raiders
        pipeline.smembers(key)
        _, potential_raiders = await pipeline.execute()

        longest = max(h["trigger"]["seconds"] for h in raid_settings["HANDLERS"])
        buckets = {h["id"]: [] for h in raid_settings["HANDLERS"]}

        #cleaning pipe!
        pipeline = self.bot.redis_pool.pipeline()

        now = datetime.fromtimestamp(time.time())
        for user in potential_raiders:
            m = member.guild.get_member(int(user))
            #discard users who are no left already
            if m is None:
                pipeline.srem(user)
                continue
            dif = now - m.joined_at.total_seconds()
            # clean up users who have been here for long enough
            if dif >= longest:
                pipeline.srem(user)
            else:
                # put them in the buckets
                for h in raid_settings["HANDLERS"]:
                    if dif < h["trigger"]["seconds"]:
                        buckets[h["id"]].append(user)

        # clean up now? you crazy, i'll do it later!
        self.bot.loop.create_task(pipeline.execute())


        # stored, fetched and sorted them, now to take care of the bad guys
        for handler in raid_settings["HANDLERS"]:
            #check if it's not disabled
            if not handler["enabled"]:
                continue

            # check if active, if it is, let that take care of it
            if member.guild.id in self.raid_trackers and handler["id"] in self.raid_trackers[member.guild.id]["handlers"]:
                for h in self.raid_trackers[member.guild.id]["handlers"]:
                    Raider.create(raid=self.raid_trackers[member.guild.id]["raid_id"], user_id=member.id, joined_at=member.joined_at)
                    self.raid_trackers[member.guild.id]["raider_ids"][member.id] = Raider.id
                    await h.handle_raider(member, self.raid_trackers[member.guild.id]["id"], self.raid_trackers[member.guild.id]["raider_ids"])
                continue

            #not active, check if we should trigger
            trigger_info = handler["trigger"]


            if len(buckets[handler["id"]]) >= trigger_info["count"]:
                #TRIGGERED
                # assign raid id, track raiders
                raid = Raid.create(guild_id=member.guild.id, start=datetime.fromtimestamp(time.time()))

                #initial logging
                GearbotLogging.log_to(member.guild.id, MessageUtils.assemble(member.guild.id, "BAD_USER", "raid_actor_triggered", name=handler["name"]))

                #create background terminator
                self.bot.loop.create_task(self.timers[handler["duration"]["type"]](member.guild.id, h, handler, handler["duration"]))

                raider_ids = dict()
                for raider in buckets[handler["id"]]:
                    Raider.create(raid=raid, user_id=raider.user_id, joined_at=raider.time)
                    raider_ids[member.id] = Raider.id

                # create tracker if missing
                if member.guild.id not in self.raid_trackers:
                    self.raid_trackers[member.guild.id] = dict(raid_id=raid.id, handlers=dict(), raider_ids=raider_ids)
                #assign the handler and call execute initial actions
                h = RaidHandler(handler)
                self.raid_trackers[member.guild.id]["handlers"][handler["id"]] = h
                await h.raid_detected(member.guild, raid.id, raider_ids)

                # deal with them
                for raider in buckets[handler["id"]]:
                    await h.handle_raider(member.guild.get_member(raider), raid.id, raider_ids)



    async def fixed_time(self, guild_id, handler, actor, data):
        await asyncio.sleep(data["delay"])
        del self.raid_trackers[guild_id][actor["id"]]
        await handler.raid_terminated()
        GearbotLogging.log_to(guild_id, MessageUtils.assemble(guild_id, "INNOCENT", 'raid_actor_terminated', name=actor["name"]))


    async def resetting(self, guild_id, handler, actor, data):
        while True:
            try:
                self.bot.wait_for("member_add", check=lambda m: m.guild.id == guild_id, timeout=data["duration"])
            except asyncio.TimeoutError:
                # no more joins! turn off the handler
                del self.raid_trackers[guild_id][actor["id"]]
                await handler.raid_terminated()
                GearbotLogging.log_to(guild_id, MessageUtils.assemble(guild_id, "INNOCENT", 'raid_actor_terminated',
                                                                      name=actor["name"]))
            else:
                pass # timer reset!






def setup(bot):
    bot.add_cog(AntiRaid(bot))
