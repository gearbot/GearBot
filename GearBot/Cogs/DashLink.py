import asyncio
import json
import time
from collections import OrderedDict
from concurrent.futures import CancelledError

import time
from datetime import datetime

import aioredis
from aioredis.pubsub import Receiver
from discord import Embed, Color, Forbidden

from Bot import TheRealGearBot
from Cogs.BaseCog import BaseCog
from Util import Configuration, GearbotLogging, Translator, server_info, DashConfig, Utils, Permissioncheckers
from Util.DashConfig import ValidationException


class DASH_PERMS:
    ACCESS = (1 << 0)
    VIEW_INFRACTIONS = (1 << 1)
    VIEW_CONFIG = (1 << 2)
    ALTER_CONFIG = (1 << 3)


def needs_perm(mask):
    def decorator(f):
        def wrap(self, message, *args, **kwargs):
            guid = message["guild_id"]
            user_id = message["user_id"]

            perms = self.get_guild_perms(guid, int(user_id))

            if perms & mask is 0:
                raise UnauthorizedException()
            return f(self, message, *args, **kwargs)

        return wrap

    return decorator


class UnauthorizedException(Exception):
    pass


class DashLink(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        bot.loop.create_task(self.init())
        self.redis_link: aioredis.Redis = None
        self.receiver = Receiver(loop=bot.loop)
        self.handlers = dict(
            heartbeat = self.still_spinning,
            guild_perms=self.guild_perm_request,
            user_info=self.user_info_request,
            guild_info=self.guild_info_request,
            get_config_section=self.get_config_section,
            update_config_section=self.update_config_section,
            languages=self.languages,
            setup_mute=self.setup_mute,
            cleanup_mute=self.cleanup_mute
        )
        # The last time we received a heartbeat, the current attempt number, how many times we have notified the owner
        self.last_dash_heartbeat = [time.time(), 0, 0]
        self.recieve_handlers = dict()
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
            self.bot.loop.create_task(self.dash_monitor())
            
            # Store the token so the dashboard can notify the bot owner if the bot goes offline
            await self.redis_link.set("bot_login_token", Configuration.get_master_var("LOGIN_TOKEN"))

            await self.redis_link.subscribe(self.receiver.channel("dash-bot-messages"))
        except OSError:
            await GearbotLogging.bot_log("Failed to connect to the dash!")

    async def dash_monitor(self):
        MAX_WARNINGS = Configuration.get_master_var("MAX_API_OUTAGE_WARNINGS", default=3)
        while True:
            if (time.time() - self.last_dash_heartbeat[0]) > 5:
                self.last_dash_heartbeat[1] += 1

                if self.last_dash_heartbeat[1] >= 3 and self.last_dash_heartbeat[2] < MAX_WARNINGS:
                    print("The dashboard API keepalive hasn't responded in over 3 minutes!")
                    
                    self.last_dash_heartbeat[2] += 1
                    self.last_dash_heartbeat[1] = 0
                    
                    # The message needs to be in English as we have no ability to get the language key of the owner
                    await GearbotLogging.message_owner(
                        self.bot,
                        f"I apologize master but it would appear that the API has gone down, please take a look when you can. This is warning {self.last_dash_heartbeat[2]}/{MAX_WARNINGS}"
                    )

            # Wait a little bit longer so the dashboard has a chance to update before we check
            await asyncio.sleep(65)

    async def _handle(self, sender, message):
        try:
            if message["type"] in self.recieve_handlers.keys():
                await self.recieve_handlers[message["type"]](message)
            else:
                try:
                    reply = dict(reply=await self.handlers[message["type"]](message), uid=message["uid"],
                                 state="OK")
                except UnauthorizedException:
                    reply = dict(uid=message["uid"], state="Unauthorized")
                except ValidationException as ex:
                    reply = dict(uid=message["uid"], state="Bad Request", errors=ex.errors)
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

    async def _receiver(self):
        async for sender, message in self.receiver.iter(encoding='utf-8', decoder=json.loads):
            self.bot.loop.create_task(self._handle(sender, message))

    async def still_spinning(self, _):
        self.last_dash_heartbeat[0] = time.time()
        self.last_dash_heartbeat[1] = 0
        self.last_dash_heartbeat[2] = 0

        return self.bot.latency

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
        info = dict()
        for guild in self.bot.guilds:
            guid = guild.id
            permission = self.get_guild_perms(guid, int(message["user_id"]))
            if permission > 0:
                info[str(guid)] = {
                    "id": str(guid),
                    "name": guild.name,
                    "permissions": permission,
                    "icon": str(guild.icon_url_as(size=256))
                }

        return OrderedDict(sorted(info.items()))

    def get_guild_perms(self, guild_id, user_id):
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return 0
        member = guild.get_member(user_id)
        if member is None:
            return 0

        mappings = {
            "ACCESS": DASH_PERMS.ACCESS,
            "INFRACTION": DASH_PERMS.VIEW_INFRACTIONS,
            "VIEW_CONFIG": DASH_PERMS.VIEW_CONFIG,
            "ALTER_CONFIG": DASH_PERMS.ALTER_CONFIG
        }

        permission = 0
        user_lvl = Permissioncheckers.user_lvl(member)
        for k, v in mappings.items():
            if user_lvl >= Configuration.get_var(guild_id, "DASH_SECURITY", k):
                permission |= v

        return permission

    @needs_perm(DASH_PERMS.ACCESS)
    async def guild_info_request(self, message):
        info = server_info.server_info_raw(self.bot.get_guild(message["guild_id"]))
        info["user_perms"] = self.get_guild_perms(message["guild_id"], int(message["user_id"]))
        info["user_level"] = Permissioncheckers.user_lvl(self.bot.get_guild(message["guild_id"]).get_member(int(message["user_id"])))
        return info

    @needs_perm(DASH_PERMS.VIEW_CONFIG)
    async def get_config_section(self, message):
        section = Configuration.get_var(message["guild_id"], message["section"])
        section = {k: [str(rid) if isinstance(rid, int) else rid for rid in v] if isinstance(v, list) else str(
            v) if isinstance(v, int) and not isinstance(v, bool) else v for k, v in section.items()}
        return section

    @needs_perm(DASH_PERMS.ALTER_CONFIG)
    async def update_config_section(self, message):
        return DashConfig.update_config_section(
            self.bot.get_guild(message["guild_id"]),
            message["section"],
            message["modified_values"],
            self.bot.get_guild(message["guild_id"]).get_member(int(message["user_id"]))
        )

    async def languages(self, message):
        return Translator.LANG_NAMES

    @needs_perm(DASH_PERMS.ALTER_CONFIG)
    async def setup_mute(self, message):
        await self.override_handler(message, "setup", dict(send_messages=False, add_reactions=False),
                                    dict(speak=False, connect=False))

    @needs_perm(DASH_PERMS.ALTER_CONFIG)
    async def cleanup_mute(self, message):
        await self.override_handler(message, "cleanup", None, None)

    async def override_handler(self, message, t, text, voice):
        guild = self.bot.get_guild(message["guild_id"])

        if not DashConfig.is_numeric(message["role_id"]):
            raise ValidationException(dict(role_id="Not a valid id"))

        role = guild.get_role(int(message["role_id"]))
        if role is None:
            raise ValidationException(dict(role_id="Not a valid id"))
        user = await Utils.get_user(message["user_id"])
        parts = {
            "role_name": Utils.escape_markdown(role.name),
            "role_id": role.id,
            "user": Utils.clean_user(user),
            "user_id": user.id
        }
        GearbotLogging.log_to(guild.id, f"config_mute_{t}_triggered", **parts)
        failed = []
        for channel in guild.text_channels:
            try:
                if text is None:
                    await channel.set_permissions(role, reason=Translator.translate(f'mute_{t}', guild.id), overwrite=None)
                else:
                    await channel.set_permissions(role, reason=Translator.translate(f'mute_{t}', guild.id), **text)
            except Forbidden as ex:
                failed.append(channel.mention)
        for channel in guild.voice_channels:
            try:
                if voice is None:
                    await channel.set_permissions(role, reason=Translator.translate(f'mute_{t}', guild.id), overwrite=None)
                else:
                    await channel.set_permissions(role, reason=Translator.translate(f'mute_{t}', guild.id), **voice)
            except Forbidden as ex:
                failed.append(Translator.translate('voice_channel', guild.id, channel=channel.name))

        await asyncio.sleep(1)  # delay logging so the channel overrides can get querried and logged
        GearbotLogging.log_to(guild.id, f"config_mute_{t}_complete", **parts)
        out = '\n'.join(failed)
        GearbotLogging.log_to(guild.id, f"config_mute_{t}_failed", **parts, count=len(failed),
                              tag_on=None if len(failed) is 0 else f'```{out}```')

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
