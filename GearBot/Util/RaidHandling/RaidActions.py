from abc import ABC, abstractmethod

from discord import Forbidden

from Util import GearbotLogging, MessageUtils, Utils


async def log(key, gid, actor, **kwargs):
    await GearbotLogging.log_to(gid, MessageUtils.assemble(gid, 'BAD_USER', key,
                                                           actor_name=Utils.escape_markdown(actor["name"]), **kwargs))

class RaidAction(ABC):

    @abstractmethod
    async def execute(self, o, data, raid_id, raider_ids, actor):
        pass

    async def reverse(self, guild, user, data, raid_id, raider_ids):
        pass

    @property
    @abstractmethod
    def is_reversable(self):
        pass


class SendMessage(RaidAction):

    async def execute(self, member, data, raid_id, raider_ids, actor):
        try:
            await member.send(data["message"].format(server_name=member.guild.name))
        except Forbidden:
            await self.log(member.guild.id, 'raid_message_failed', actor, )

    @property
    def is_reversable(self):
        return False


class Mute(RaidAction):

    async def execute(self, member, data, raid_id, raider_ids, actor):
        pass

    async def reverse(self, guild, user, data, raid_id, raider_ids):
        pass

    @property
    def is_reversable(self):
        return True


class Kick(RaidAction):

    async def execute(self, member, data, raid_id, raider_ids, actor):
        pass

    async def reverse(self, guild, user, data, raid_id, raider_ids):
        pass

    @property
    def is_reversable(self):
        return True


class Ban(RaidAction):

    async def execute(self, member, data, raid_id, raider_ids, actor):
        pass

    async def reverse(self, guild, user, data, raid_id, raider_ids):
        pass

    @property
    def is_reversable(self):
        return True


class DmSomeone(RaidAction):

    async def execute(self, guild, data, raid_id, raider_ids, actor):
        member = guild.get_member(data["user_id"])
        if member is None:
            await log(member.guild.id, 'raid_notification_failed', actor, user_id=data["user_id"])
            return
        try:
            await member.send(data["message"].format(server_name=member.guild.name))
        except Forbidden:
            await log(member.guild.id, 'raid_notification_forbidden', actor, user_name=Utils.username_from_user(member), user_id=member.id)

    @property
    def is_reversable(self):
        return False


handlers = {
    "send_message": SendMessage(),
    "dm_someone": DmSomeone(),
    "mute_raider": Mute(),
    "kick_raider": Kick(),
    "ban_raider": Ban()
}
