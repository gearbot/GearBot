import json

import aioredis
from aioredis.pubsub import Receiver

from Bot import TheRealGearBot
from Bot.GearBot import GearBot
from Util import Configuration, GearbotLogging


class DashLink:

    def __init__(self, bot) -> None:
        self.bot:GearBot = bot
        bot.loop.create_task(self.init())
        self.redis_link = None
        self.receiver = Receiver(loop=bot.loop)
        self.handlers = dict(
            guild_perm_request=self.guild_perm_request
        )
        self.task = self._receiver()

    def __unload(self):
        self.bot.loop.create_task(self._unload())

    async def _unload(self):
        for c in self.receiver.channels.values():
            self.redis_link.unsubscribe(c)
        self.receiver.stop()
        self.redis_link.close()
        await self.redis_link.wait_closed()

    async def init(self):
        try:
            self.redis_link = await aioredis.create_redis_pool(
                (Configuration.get_master_var('REDIS_HOST', "localhost"), Configuration.get_master_var('REDIS_PORT', 6379)),
                encoding="utf-8", db=0, maxsize=2) # size 2: one send, one receive
            self.bot.loop.create_task(self._receiver())
            await self.redis_link.subscribe(self.receiver.channel("dash-bot-messages"))
        except OSError:
            await GearbotLogging.bot_log("Failed to connect to the dash!")

    async def _receiver(self):
        async for sender, message in self.receiver.iter(encoding='utf-8', decoder=json.loads):
            try:
                await self.handlers[message["type"]](message)
            except Exception as e:
                await TheRealGearBot.handle_exception("Dash message handling", self.bot, e, None, None, None, message)

    async def send_reply(self, data):
        await self.redis_link.publish_json("bot-dash-messages", data)


    async def guild_perm_request(self, message):
        permissions = dict()
        for guid in message["guild_list"]:
            guid = int(guid)
            guild = self.bot.get_guild(guid)
            permission = 0
            if guild is not None:
                member = guild.get_member(int(message["user_id"]))
                mod_roles = Configuration.get_var(guid, "MOD_ROLES")
                if member.guild_permissions.ban_members or any(r.id in mod_roles for r in member.roles):
                    permission |= (1 << 0) # dash access
                    permission |= (1 << 1) # infraction access

                admin_roles = Configuration.get_var(guid, "ADMIN_ROLES")
                if member.guild_permissions.administrator or any(r.id in admin_roles for r in member.roles):
                    permission |= (1 << 0)  # dash access
                    permission |= (1 << 2)  # config read access
                    permission |= (1 << 3)  # config write access

            permissions[guid] = permission
        await self.send_reply(dict(uid=message["uid"], permissions=permissions))





def setup(bot):
    bot.add_cog(DashLink(bot))