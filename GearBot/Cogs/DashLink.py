import json
from concurrent.futures import CancelledError

import time
from datetime import datetime

import aioredis
from aioredis.pubsub import Receiver
from discord import Embed, Color

from Bot import TheRealGearBot
from Cogs.BaseCog import BaseCog
from Util import Configuration, GearbotLogging, Translator, server_info

from time import perf_counter_ns


class UnauthorizedException(Exception):
    pass


class DashLink(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        bot.loop.create_task(self.init())
        self.redis_link = None
        self.receiver = Receiver(loop=bot.loop)
        self.handlers = dict(
            guild_perms=self.guild_perm_request,
            user_info=self.user_info_request,
            guild_info=self.guild_info_request
        )
        self.recieve_handlers = dict(

        )
        self.last_update = datetime.now()
        self.to_log = dict()
        self.update_message = None

        if Configuration.get_master_var("TRANSLATIONS", dict(SOURCE="SITE", CHANNEL=0, KEY="", LOGIN="", WEBROOT=""))[
            "SOURCE"] == 'CROWDIN':
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
                (Configuration.get_master_var('REDIS_HOST', "localhost"),
                 Configuration.get_master_var('REDIS_PORT', 6379)),
                encoding="utf-8", db=0, maxsize=2)  # size 2: one send, one receive
            self.bot.loop.create_task(self._receiver())
            await self.redis_link.subscribe(self.receiver.channel("dash-bot-messages"))
        except OSError:
            await GearbotLogging.bot_log("Failed to connect to the dash!")

    async def _receiver(self):
        async for sender, message in self.receiver.iter(encoding='utf-8', decoder=json.loads):
            try:
                if message["type"] in self.recieve_handlers.keys():
                    await self.recieve_handlers[message["type"]](message)
                else:
                    try:
                        reply = dict(reply=await self.handlers[message["type"]](message), uid=message["uid"],
                                     state="OK")
                    except UnauthorizedException:
                        reply = dict(uid=message["uid"], state="Unauthorized")
                    except CancelledError:
                        return
                    except Exception as ex:
                        reply = dict(uid=message["uid"], state="Failed")
                        await self.redis_link.publish_json("bot-dash-messages", reply)
                        raise ex
                    await self.redis_link.publish_json("bot-dash-messages", reply)
            except CancelledError:
                return
            except Exception as e:
                await TheRealGearBot.handle_exception("Dash message handling", self.bot, e, None, None, None, message)

    async def user_info_request(self, message):
        user_id = message["user_id"]
        user_info = await self.bot.fetch_user(user_id)
        return_info = {
            "username": user_info.name,
            "discrim": user_info.discriminator,
            "avatar_url": str(user_info.avatar_url_as(size=256)),
            "bot_admin_status": await self.bot.is_owner(user_info) or user_id in Configuration.get_master_var(
                "BOT_ADMINS", [])
        }

        return return_info

    async def guild_perm_request(self, message):
        start_time = perf_counter_ns()
        info = dict()
        for guild in self.bot.guilds:
            guid = guild.id
            permission = self.get_guild_perms(guild, int(message["user_id"]))
            if permission > 0:
                info[guid] = {
                    "name": guild.name,
                    "permissions": permission,
                    "icon": str(guild.icon_url_as(size=256))
                }

        finish_time = perf_counter_ns()
        final_time = (finish_time - start_time) / 1000000
        print("The perms calculation operation took: " + str(final_time))

        return info

    def get_guild_perms(self, guild_id, user_id):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return 0
        member = guild.get_member(user_id)
        if member is None:
            return 0
        permission = 0
        mod_roles = Configuration.get_var(guild_id, "MOD_ROLES")
        if member.guild_permissions.ban_members or any(r.id in mod_roles for r in member.roles):
            permission |= (1 << 0)  # dash access
            permission |= (1 << 1)  # infraction access

        admin_roles = Configuration.get_var(guild_id, "ADMIN_ROLES")
        if member.guild_permissions.administrator or any(r.id in admin_roles for r in member.roles):
            permission |= (1 << 0)  # dash access
            permission |= (1 << 2)  # config read access
            permission |= (1 << 3)  # config write access
        return permission

    async def guild_info_request(self, message):
        guid = message["guid"]
        user_id = message["user_id"]

        if self.get_guild_perms(guid, int(user_id)) & (1 << 0) is 0:
            raise UnauthorizedException()

        return server_info.server_info_raw(self.bot.get_guild(guid))

    # crowdin
    async def crowdin_webhook(self, message):
        code = message["info"]["language"]
        await Translator.update_lang(code)
        if (datetime.now() - self.last_update).seconds > 5 * 60:
            self.update_message = None
            self.to_log = dict()
        if code not in self.to_log:
            self.to_log[code] = 0
        self.to_log[code] += 1

        embed = Embed(color=Color(0x1183f6), timestamp=datetime.utcfromtimestamp(time.time()),
                      description=f"**Live translation update summary!**\n" + '\n'.join(
                          f"{Translator.LANG_NAMES[code]} : {count}" for code, count in self.to_log.items()))
        if self.update_message is None:
            self.update_message = await Translator.get_translator_log_channel()(embed=embed)
        else:
            await self.update_message.edit(embed=embed)

        self.last_update = datetime.now()


def setup(bot):
    bot.add_cog(DashLink(bot))
