import json

import aioredis
from aioredis.pubsub import Receiver

from Bot import TheRealGearBot
from Cogs.BaseCog import BaseCog
from Util import Configuration, GearbotLogging


class DashLink(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        bot.loop.create_task(self.init())
        self.redis_link = None
        self.receiver = Receiver(loop=bot.loop)
        self.handlers = dict(
            guild_perm_request=self.guild_perm_request
        )
        self.recieve_handlers = dict(

        )

        if Configuration.get_master_var("TRANSLATIONS", dict(SOURCE="SITE", CHANNEL=0, KEY= "", LOGIN="", WEBROOT=""))["SOURCE"] == 'CROWDIN':
            self.recieve_handlers["crowdin_webhook"] = self.crowdin_webhook
        self.task = self._receiver()

    def cog_unload(self):
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
                if message["type"] in self.recieve_handlers.keys():
                    await self.recieve_handlers[message["type"]](message)
                reply = dict(reply=await self.handlers[message["type"]](message), uid=message["uid"])
                await self.redis_link.publish_json("bot-dash-messages", reply)
            except Exception as e:
                await TheRealGearBot.handle_exception("Dash message handling", self.bot, e, None, None, None, message)


    async def guild_perm_request(self, message):
        info = dict()
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

            if permission > 0:
                info[guid] = dict(name=guild.name, permissions=permission, icon=guild.icon_url_as(size=256))
        return info



    #crowdin
    async def crowdin_webhook(self, message):
        info = message["info"]
        





def setup(bot):
    bot.add_cog(DashLink(bot))