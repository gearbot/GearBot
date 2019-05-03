import time
from abc import ABC, abstractmethod

from discord import Forbidden, NotFound

from Util import GearbotLogging, Utils, Configuration, InfractionUtils
from database import DatabaseConnector


async def log(key, gid, shield, **kwargs):
    await GearbotLogging.log_to(gid, key, shield_name=Utils.escape_markdown(shield["name"]), **kwargs)

class RaidAction(ABC):

    @abstractmethod
    async def execute(self, bot, o, data, raid_id, raider_ids, shield):
        pass

    async def reverse(self, bot, guild, user, data, raid_id, raider_id):
        pass

    @property
    @abstractmethod
    def is_reversable(self):
        pass


class SendMessage(RaidAction):

    async def execute(self, bot, guild, data, raid_id, raider_ids, shield):
        try:
            channel =  guild.get_channel(data["channel"])
            if channel is not None:
                await channel.send(data["message"].format(server_name=guild.name))
        except Forbidden:
            await log(guild.id, 'raid_message_failed', shield)

    @property
    def is_reversable(self):
        return False

class DMRaider(RaidAction):
    async def execute(self, bot, member, data, raid_id, raider_ids, shield):
        try:
            await member.send(data["message"].format(server_name=member.guild.name))
        except (Forbidden, NotFound):
            pass

    @property
    def is_reversable(self):
        return False

class Mute(RaidAction):

    async def execute(self, bot, member, data, raid_id, raider_ids, shield):
        role = member.guild.get_role(Configuration.get_var(member.guild.id, "MUTE_ROLE"))
        if role is None:
            GearbotLogging.log_to(member.guild.id, 'raid_mute_failed_no_role')
        else:
            duration = data["duration"]
            reason = f"Raider muted by raid shield {shield['name']} in raid {raid_id}"
            await member.add_roles(role, reason=reason)
            until = time.time() + duration
            i = InfractionUtils.add_infraction(member.guild.id, member.id, member.guild.me.id, "Mute", reason, end=until)
            DatabaseConnector.RaidAction.create(raider=raider_ids[member.id], action="mute_raider", infraction=i)

    async def reverse(self, bot, guild, user, data, raid_id, raider_id):
        pass

    @property
    def is_reversable(self):
        return True


class Kick(RaidAction):

    async def execute(self, bot, member, data, raid_id, raider_ids, shield):
        bot.data["forced_exits"].add(f"{member.guild.id}-{member.id}")
        reason=f"Raider kicked by raid shield {shield['name']} in raid {raid_id}"
        await member.kick(reason=reason)
        i = InfractionUtils.add_infraction(member.guild.id, member.id, bot.user.id, 'Kick', reason, active=False)
        GearbotLogging.log_to(member.guild.id, 'kick_log', member.guild.id,
                                                    user=Utils.clean_user(member), user_id=member.id,
                                                    moderator=Utils.clean_user(member.guild.me), moderator_id=bot.user.id,
                                                    reason=reason, inf=i.id)
        DatabaseConnector.RaidAction.create(raider=raider_ids[member.id], action="mute_raider", infraction=i)

    async def reverse(self, bot, guild, user, data, raid_id, raider_id):
        pass

    @property
    def is_reversable(self):
        return True


class Ban(RaidAction):

    async def execute(self, bot, member, data, raid_id, raider_ids, shield):
        bot.data["forced_exits"].add(f"{member.guild.id}-{member.id}")
        reason = f"Raider banned by raid shield {shield['name']} in raid {raid_id}"
        await member.ban(reason=reason,
                            delete_message_days=1 if data["clean_messages"] else 0)
        i = InfractionUtils.add_infraction(member.guild.id, member.id, bot.user.id, "Ban", reason)
        GearbotLogging.log_to(member.guild.id, 'ban_log', user=Utils.clean_user(member), user_id=member.id,
                                                    moderator=Utils.clean_user(bot.user), moderator_id=bot.user.id,
                                                    reason=reason, inf=i.id)

    async def reverse(self, bot, guild, user, data, raid_id, raider_id):
        pass

    @property
    def is_reversable(self):
        return True


class DmSomeone(RaidAction):

    async def execute(self, bot, guild, data, raid_id, raider_ids, shield):
        member = guild.get_member(data["user_id"])
        if member is None:
            await log(member.guild.id, 'raid_notification_failed', shield, user_id=data["user_id"])
            return
        try:
            await member.send(data["message"].format(server_name=member.guild.name))
        except Forbidden:
            await log(member.guild.id, 'raid_notification_forbidden', shield, user_name=Utils.username_from_user(member), user_id=member.id)

    @property
    def is_reversable(self):
        return False

class LowerShield(RaidAction):

    async def execute(self, bot, guild, data, raid_id, raider_ids, shield):
        cog = bot.get_cog("AntiRaid")
        if data["shield_id"] in cog.raid_trackers[guild.id]["SHIELDS"]:
            cog.raid_trackers[guild.id]["SHIELDS"][data["shield_id"]].shield_terminated()
            del cog.raid_trackers[guild.id]["SHIELDS"][data["shield_id"]]
        else:
            # not triggered yet, prevent activation
            cog.raid_trackers[guild.id]["triggered"].add(data["shield_id"])


    @property
    def is_reversable(self):
        return False


class SendDash(RaidAction):

    async def execute(self, bot, guild, data, raid_id, raider_ids, shield):
        cog = bot.get_cog("AntiRaid")
        pass


    @property
    def is_reversable(self):
        return False


handlers = {
    "send_message": SendMessage(),
    "dm_someone": DmSomeone(),
    "mute_raider": Mute(),
    "kick_raider": Kick(),
    "ban_raider": Ban(),
    "lower_shield": LowerShield(),
    "dm_raider": DMRaider(),
    "send_dash": SendDash()
}
