from Util import GearbotLogging
from Util.RaidHandling import RaidActions


class RaidShield:

    def __init__(self, shield_info) -> None:
        self.shield_name=shield_info["name"]
        self.start_actions = [action for action in shield_info["actions"]["triggered"]]
        self.raider_actions = [action for action in shield_info["actions"]["raider"]]
        self.termination_actions = [action for action in shield_info["actions"]["terminated"]]

    async def raid_detected(self, bot, guild, raid_id, raider_ids, shield):
        GearbotLogging.log_to(guild.id, "raid_shield_triggered", raid_id=raid_id, name=self.shield_name)
        await self.handle_actions(self.start_actions, bot, guild, raid_id, raider_ids, shield)

    async def handle_raider(self, bot, raider, raid_id, raider_ids, shield):
        await self.handle_actions(self.raider_actions, bot, raider, raid_id, raider_ids, shield)

    async def shield_terminated(self, bot, guild, raid_id, raider_ids, shield):
        GearbotLogging.log_to(guild.id, "raid_shield_terminated", raid_id=raid_id, name=self.shield_name)
        await self.handle_actions(self.termination_actions, bot, guild, raid_id, raider_ids, shield)

    async def handle_actions(self, actions, bot, o, raid_id, raider_ids, shield):
        for a in actions:
            action = RaidActions.handlers[a["type"]]
            await action.execute(bot, o, a["action_data"], raid_id, raider_ids, shield)
