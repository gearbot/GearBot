import time
from datetime import datetime

import discord

from Bot.GearBot import GearBot
from Util import Configuration
from Util.RaidHandling.RaidHandler import RaidHandler
from database.DatabaseConnector import JoinEvent, Raid, Raider


class AntiRaid:
    def __init__(self, bot):
        self.bot: GearBot = bot
        self.raid_trackers = dict()

    async def on_member_join(self, member: discord.Member):
        raid_settings = Configuration.get_var(member.guild.id, "RAID_HANDLING")
        if not raid_settings["enabled"]:
            return

        # insert join event
        JoinEvent.create(user_id=member.id, guild_id=member.guild.id, time=member.joined_at)


        # find active buckets
        for handler in raid_settings["HANDLERS"]:
            #check if it's not disabled
            if not handler["enabled"]:
                continue

            # check if active, if it is, let that take care of it
            if member.guild.id in self.raid_trackers and handler["id"] in self.raid_trackers[member.guild.id]["handlers"]:
                for h in self.raid_trackers[member.guild.id]["handlers"]:
                    await h.handle_raider(member, self.raid_trackers[member.guild.id]["id"], self.raid_trackers[member.guild.id]["raider_ids"])
                continue

            #not active, check if we should trigger
            trigger_info = handler["trigger"]

            raiders = JoinEvent.select().where((JoinEvent.guild_id ==  member.guild.id) & (JoinEvent.time > datetime.fromtimestamp(time.time() - trigger_info["seconds"]))).execute()
            if len(raiders) >= trigger_info["count"]:
                #TRIGGERED

                # assign raid id, track raiders
                raid = Raid.create(guild_id=member.guild.id, start=datetime.fromtimestamp(time.time()))
                raider_ids = dict()
                for raider in raiders:
                    Raider.create(raid=raid, user_id=raider.user_id, joined_at=raider.time)
                    raider_ids[member.id] = Raider.id

                # create tracker if missing
                if member.guild.id not in self.raid_trackers:
                    self.raid_trackers[member.guild.id] = dict(raid_id=raid.id, handlers=dict(), raider_ids=raider_ids)
                #assign the handler and call execute initial actions
                h = RaidHandler(handler)
                self.raid_trackers[member.guild.id]["handlers"][handler["id"]] = h
                await h.raid_detected(member.guild, raid.id, raider_ids)


def setup(bot):
    bot.add_cog(AntiRaid(bot))
