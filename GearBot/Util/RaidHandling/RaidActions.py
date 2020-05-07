import time
from abc import ABC, abstractmethod

from discord import Forbidden, NotFound

from Bot import TheRealGearBot
from Util import GearbotLogging, Utils, Configuration, InfractionUtils
from database import DatabaseConnector


def log(gid, key, shield, **kwargs):
    GearbotLogging.log_key(gid, key, shield_name=Utils.escape_markdown(shield["name"]), **kwargs)


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
            channel = guild.get_channel(data["channel"])
            if channel is not None:
                await channel.send(data["message"].format(server_name=guild.name))
            else:
                log(guild.id, 'raid_message_failed_missing_channel', shield, cid=data["channel"])
                GearbotLogging.log_raw(guild.id, 'raid_message_failed_missing_channel', data["message"].format(server_name=guild.name))
        except Forbidden:
            log(guild.id, 'raid_message_failed_channel', shield, cid=data["channel"])
            GearbotLogging.log_raw(guild.id, 'raid_message_failed_missing_channel', data["message"].format(server_name=guild.name))
        except Exception as ex:
            log(guild.id, 'raid_message_failed_channel_unknown_error', shield, cid=data["channel"])
            GearbotLogging.log_raw(guild.id, 'raid_message_failed_missing_channel', data["message"].format(server_name=guild.name))
            await TheRealGearBot.handle_exception('RAID NOTIFICATION FAILURE', bot, ex)

    @property
    def is_reversable(self):
        return False


class DMRaider(RaidAction):
    async def execute(self, bot, member, data, raid_id, raider_ids, shield):
        try:
            await member.send(data["message"].format(server_name=member.guild.name))
        except NotFound:
            log(member.guild.id, 'raid_message_user_not_found', shield, user_name=Utils.escape_markdown(member),
                user_id=member.id)
        except Forbidden:
            log(member.guild.id, 'raid_message_user_forbidden', shield, user_name=Utils.escape_markdown(member),
                user_id=member.id)
        except Exception as ex:
            log(member.guild.id, 'raid_message_user_unknown_error', shield, user_name=Utils.escape_markdown(member),
                user_id=member.id)
            await TheRealGearBot.handle_exception('RAID DM FAILURE', bot, ex)

    @property
    def is_reversable(self):
        return False


class Mute(RaidAction):

    async def execute(self, bot, member, data, raid_id, raider_ids, shield):
        role = member.guild.get_role(Configuration.get_var(member.guild.id, "ROLES", "MUTE_ROLE"))
        if role is None:
            GearbotLogging.log_key(member.guild.id, 'raid_mute_failed_no_role')
        else:
            duration = data["duration"]
            reason = f"Raider muted by raid shield {shield['name']} in raid {raid_id}"
            try:
                await member.add_roles(role, reason=reason)
            except NotFound:
                pass
            except Forbidden:
                log(member.guild.id, 'raid_mute_forbidden', shield, user_name=Utils.escape_markdown(member),
                    user_id=member.id)
            except Exception as ex:
                log(member.guild.id, 'raid_mute_unknown_error', shield, user_name=Utils.escape_markdown(member),
                    user_id=member.id)
                await TheRealGearBot.handle_exception('RAID MUTE FAILURE', bot, ex)
            finally:
                until = time.time() + duration
                i = await InfractionUtils.add_infraction(member.guild.id, member.id, member.guild.me.id, "Mute", reason,
                                                   end=until)

    async def reverse(self, bot, guild, user, data, raid_id, raider_id):
        pass

    @property
    def is_reversable(self):
        return True


class Kick(RaidAction):

    async def execute(self, bot, member, data, raid_id, raider_ids, shield):
        bot.data["forced_exits"].add(f"{member.guild.id}-{member.id}")
        reason = f"Raider kicked by raid shield {shield['name']} in raid {raid_id}"
        try:
            await member.kick(reason=reason)
        except NotFound:
            pass
        except Forbidden:
            log(member.guild.id, 'raid_kick_forbidden', shield, user_name=Utils.escape_markdown(member),
                user_id=member.id)
        except Exception as ex:
            log(member.guild.id, 'raid_kick_unknown_error', shield, user_name=Utils.escape_markdown(member),
                user_id=member.id)
            await TheRealGearBot.handle_exception('RAID KICK FAILURE', bot, ex)
        finally:
            i = await  InfractionUtils.add_infraction(member.guild.id, member.id, bot.user.id, 'Kick', reason, active=False)
            GearbotLogging.log_key(member.guild.id, 'kick_log',
                                   user=Utils.clean_user(member), user_id=member.id,
                                   moderator=Utils.clean_user(member.guild.me), moderator_id=bot.user.id,
                                   reason=reason, inf=i.id)

    async def reverse(self, bot, guild, user, data, raid_id, raider_id):
        pass

    @property
    def is_reversable(self):
        return True


class Ban(RaidAction):

    async def execute(self, bot, member, data, raid_id, raider_ids, shield):
        bot.data["forced_exits"].add(f"{member.guild.id}-{member.id}")
        reason = f"Raider banned by raid shield {shield['name']} in raid {raid_id}"
        try:
            await member.ban(reason=reason,
                             delete_message_days=1 if data["clean_messages"] else 0)
        except Forbidden:
            log(member.guild.id, 'raid_ban_forbidden', shield, user_name=Utils.escape_markdown(member),
                user_id=member.id)
        except Exception as ex:
            log(member.guild.id, 'raid_ban_unknown_error', shield, user_name=Utils.escape_markdown(member),
                user_id=member.id)
            await TheRealGearBot.handle_exception('RAID BAN FAILURE', bot, ex)
        finally:
            i = await InfractionUtils.add_infraction(member.guild.id, member.id, bot.user.id, "Ban", reason)
            GearbotLogging.log_key(member.guild.id, 'ban_log', user=Utils.clean_user(member), user_id=member.id,
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
            log(member.guild.id, 'raid_notification_failed', shield, user_id=data["user_id"])
            return
        try:
            await member.send(data["message"].format(server_name=member.guild.name))
        except Forbidden:
            log(member.guild.id, 'raid_notification_forbidden', shield, user_name=Utils.username_from_user(member),
                user_id=member.id)

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
