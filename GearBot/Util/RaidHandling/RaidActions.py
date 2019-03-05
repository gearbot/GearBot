from abc import ABC, abstractmethod

class RaidAction(ABC):

    @abstractmethod
    async def execute(self, member, data, raid_id):
        pass

    async def reverse(self, guild, user, data, raid_id):
        pass

    @property
    @abstractmethod
    def is_reversable(self):
        pass


class SendMessage(RaidAction):

    async def execute(self, member, data, raid_id):
        pass


    @property
    def is_reversable(self):
        return False


class Mute(RaidAction):

    async def execute(self, member, data, raid_id):
        pass

    async def reverse(self, guild, user, data, raid_id):
        pass

    @property
    def is_reversable(self):
        return True


class Kick(RaidAction):

    async def execute(self, member, data, raid_id):
        pass

    async def reverse(self, guild, user, data, raid_id):
        pass

    @property
    def is_reversable(self):
        return True


class Ban(RaidAction):

    async def execute(self, member, data, raid_id):
        pass

    async def reverse(self, guild, user, data, raid_id):
        pass

    @property
    def is_reversable(self):
        return True

handlers = {
    "send_message": SendMessage(),
    "mute_raider": Mute(),
    "kick_raider": Kick(),
    "ban_raider": Ban()
}
