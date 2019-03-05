from Util.RaidHandling import RaidActions


class RaidHandler:

    def __init__(self, handler_info) -> None:
        self.start_actions = [RaidActions.handlers[name] for name in handler_info["triggered"]]
        self.raider_actions = [RaidActions.handlers[name] for name in handler_info["raider"]]
        self.termination_actions = [RaidActions.handlers[name] for name in handler_info["terminated"]]

    async def raid_detected(self, guild, raid_id, raider_ids):
        await self.handle_actions(self.start_actions, guild, raid_id, raider_ids)

    async def handle_raider(self, raider, raid_id, raider_ids):
        await self.handle_actions(self.raider_actions, raider, raid_id, raider_ids)

    async def raid_terminated(self, guild, raid_id, raider_ids):
        await self.handle_actions(self.termination_actions, guild, raid_id, raider_ids)

    async def handle_actions(self, actions, o, raid_id, raider_ids):
        for a in actions:
            await a(o, raid_id, raider_ids)
