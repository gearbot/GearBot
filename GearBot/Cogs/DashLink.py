import asyncio
import json
from concurrent.futures import CancelledError

import time
from datetime import datetime

import aioredis
from aioredis.pubsub import Receiver
from discord import Embed, Color, Forbidden
from discord.ext import commands

from Bot import TheRealGearBot
from Cogs.BaseCog import Gear
from Util import Configuration, GearbotLogging, Translator, DashConfig, Utils, Update, DashUtils
from Util.DashConfig import ValidationException
from Util.DashUtils import DASH_PERMS, get_guild_perms


def get_info(message):
    return int(message["guild_id"]), int(message["user_id"])


def needs_perm(mask):
    def decorator(f):
        def wrap(self, message, *args, **kwargs):
            guild_id, user_id = get_info(message)

            guild = self.bot.get_guild(guild_id)
            if guild is None:
                raise UnauthorizedException()
            perms = get_guild_perms(guild.get_member(user_id))

            if perms & mask is 0:
                raise UnauthorizedException()
            return f(self, message, *args, **kwargs)

        return wrap

    return decorator


class UnauthorizedException(Exception):
    pass


class DashLink(Gear):

    def __init__(self, bot):
        super().__init__(bot)
        bot.loop.create_task(self.init())
        self.redis_link: aioredis.Redis = None
        self.receiver = Receiver(loop=bot.loop)
        self.handlers = dict(
            question=self.question,
            update=self.update,
            user_guilds=self.user_guilds,
            user_guilds_end=self.user_guilds_end,
            guild_info_watch=self.guild_info_watch,
            guild_info_watch_end=self.guild_info_watch_end,
            usernames_request=self.usernames_request
        )
        self.question_handlers = dict(
            heartbeat=self.still_spinning,
            user_info=self.user_info_request,
            get_guild_settings=self.get_guild_settings,
            save_guild_settings=self.save_guild_settings,
            replace_guild_settings=self.replace_guild_settings,
            setup_mute=self.setup_mute,
            cleanup_mute=self.cleanup_mute,
            cache_info=self.cache_info,
            guild_user_perms=self.guild_user_perms,
            get_user_guilds=self.get_user_guilds,
            get_guild_info=self.get_guild_info,
        )
        # The last time we received a heartbeat, the current attempt number, how many times we have notified the owner
        self.last_dash_heartbeat = [time.time(), 0, 0]
        self.last_update = datetime.now()
        self.to_log = dict()
        self.update_message = None

        if Configuration.get_master_var("TRANSLATIONS", dict(SOURCE="SITE", CHANNEL=0, KEY="", LOGIN="", WEBROOT=""))[
            "SOURCE"] == 'CROWDIN':
            self.handlers["crowdin_webhook"] = self.crowdin_webhook
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

            if Configuration.get_master_var("DASH_OUTAGE")["outage_detection"]:
                self.bot.loop.create_task(self.dash_monitor())

            await self.redis_link.subscribe(self.receiver.channel("dash-bot-messages"))
            await self.redis_link.publish_json("bot-dash-messages", {
                'type': 'cache_info',
                'message': await self.cache_info()
            })

        except OSError:
            await GearbotLogging.bot_log("Failed to connect to the dash!")

    async def dash_monitor(self):
        DASH_OUTAGE_INFO: dict = Configuration.get_master_var("DASH_OUTAGE")
        DASH_OUTAGE_CHANNEl = DASH_OUTAGE_INFO["dash_outage_channel"]
        MAX_WARNINGS = DASH_OUTAGE_INFO["max_bot_outage_warnings"]
        BOT_OUTAGE_PINGED_ROLES = DASH_OUTAGE_INFO["dash_outage_pinged_roles"]

        while True:
            if (time.time() - self.last_dash_heartbeat[0]) > 5:
                self.last_dash_heartbeat[1] += 1

                if self.last_dash_heartbeat[1] >= 3 and self.last_dash_heartbeat[2] < MAX_WARNINGS:
                    print("The dashboard API keepalive hasn't responded in over 3 minutes!")

                    self.last_dash_heartbeat[2] += 1
                    self.last_dash_heartbeat[1] = 0

                    if DASH_OUTAGE_CHANNEl:
                        outage_message = DASH_OUTAGE_INFO["dash_outage_embed"]

                        # Apply the timestamp
                        outage_message["timestamp"] = datetime.now().isoformat()

                        # Set the color to the format Discord understands
                        outage_message["color"] = outage_message["color"]

                        # Generate the custom message and role pings
                        notify_message = DASH_OUTAGE_INFO["dash_outage_message"]
                        if BOT_OUTAGE_PINGED_ROLES:
                            pinged_roles = []
                            for role_id in BOT_OUTAGE_PINGED_ROLES:
                                pinged_roles.append(f"<@&{role_id}>")

                            notify_message += f" Pinging: {', '.join(pinged_roles)}"

                        try:
                            outage_channel = self.bot.get_channel(DASH_OUTAGE_CHANNEl)
                            await outage_channel.send(notify_message, embed=Embed.from_dict(outage_message))
                        except Forbidden:
                            GearbotLogging.error(
                                "We couldn't access the specified channel, the notification will not be sent!")

            # Wait a little bit longer so the dashboard has a chance to update before we check
            await asyncio.sleep(65)

    async def _handle(self, sender, message):
        try:
            await self.handlers[message["type"]](message["message"])
        except CancelledError:
            return
        except Exception as e:
            await TheRealGearBot.handle_exception("Dash message handling", self.bot, e, None, None, None, message)

    async def send_to_dash(self, channel, **kwargs):
        await self.redis_link.publish_json("bot-dash-messages", dict(type=channel, message=kwargs))

    async def question(self, message):
        try:
            reply = dict(reply=await self.question_handlers[message["type"]](message["data"]), state="OK",
                         uid=message["uid"])
        except UnauthorizedException:
            reply = dict(uid=message["uid"], state="Unauthorized")
        except ValidationException as ex:
            reply = dict(uid=message["uid"], state="Bad Request", errors=ex.errors)
        except CancelledError:
            return
        except Exception as ex:
            reply = dict(uid=message["uid"], state="Failed")
            await self.send_to_dash("reply", **reply)
            raise ex
        await self.send_to_dash("reply", **reply)

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

    async def user_guilds(self, message):
        user_id = int(message["user_id"])
        self.bot.dash_guild_users.add(user_id)

    async def get_user_guilds(self, message):
        return DashUtils.get_user_guilds(self.bot, message["user_id"])

    async def user_guilds_end(self, message):
        user_id = int(message["user_id"])
        self.bot.dash_guild_users.remove(user_id)

    async def guild_user_perms(self, message):
        guild = self.bot.get_guild(int(message["guild_id"]))
        if guild is None:
            return 0
        return DashUtils.get_guild_perms(guild.get_member(int(message["user_id"])))

    @needs_perm(DASH_PERMS.ACCESS)
    async def get_guild_info(self, message):
        guild_id, user_id = get_info(message)
        return DashUtils.assemble_guild_info(self.bot, self.bot.get_guild(guild_id).get_member(user_id))

    @needs_perm(DASH_PERMS.ACCESS)
    async def guild_info_watch(self, message):
        # start tracking info
        guild_id, user_id = get_info(message)
        if guild_id not in self.bot.dash_guild_watchers:
            self.bot.dash_guild_watchers[guild_id] = set()
        self.bot.dash_guild_watchers[guild_id].add(user_id)

    async def guild_info_watch_end(self, message):
        guild_id, user_id = get_info(message)
        if guild_id in self.bot.dash_guild_watchers:
            users = self.bot.dash_guild_watchers[guild_id]
            users.remove(user_id)
            if len(users) is 0:
                del self.bot.dash_guild_watchers[guild_id]

    async def send_guild_info_update_to_all(self, guild):
        if guild.id in self.bot.dash_guild_watchers:
            for user in self.bot.dash_guild_watchers[guild.id]:
                await self.send_guild_info(guild.get_member(user))

    async def send_guild_info(self, member):
        await self.send_to_dash("guild_update", user_id=member.id, guild_id=member.guild.id,
                                info=DashUtils.assemble_guild_info(self.bot, member))

    @needs_perm(DASH_PERMS.VIEW_CONFIG)
    async def get_guild_settings(self, message):
        section = Configuration.get_var(int(message["guild_id"]), message["section"])
        section = {k: [str(rid) if isinstance(rid, int) else rid for rid in v] if isinstance(v, list) else str(
            v) if isinstance(v, int) and not isinstance(v, bool) else v for k, v in section.items()}
        return section

    @needs_perm(DASH_PERMS.ALTER_CONFIG)
    async def save_guild_settings(self, message):
        guild_id, user_id = get_info(message)
        guild = self.bot.get_guild(guild_id)
        return DashConfig.update_config_section(
            guild,
            message["section"],
            message["modified_values"],
            guild.get_member(user_id)
        )

    @needs_perm(DASH_PERMS.ALTER_CONFIG)
    async def replace_guild_settings(self, message):
        guild_id, user_id = get_info(message)
        guild = self.bot.get_guild(guild_id)
        return DashConfig.update_config_section(
            guild,
            message["section"],
            message["modified_values"],
            guild.get_member(user_id),
            replace=True
        )

    async def cache_info(self, message=None):
        return {
            'languages': Translator.LANG_NAMES,
            'logging': {k: list(v.keys()) for k, v in GearbotLogging.LOGGING_INFO.items()}
        }

    @needs_perm(DASH_PERMS.ALTER_CONFIG)
    async def setup_mute(self, message):
        await self.override_handler(
            message,
            "setup",
            dict(send_messages=False, add_reactions=False),
            dict(speak=False, connect=False, stream=False)
        )

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
        if role.id == guild.id:
            raise ValidationException(dict(role_id="The @everyone role can't be used for muting people"))
        if role.managed:
            raise ValidationException(
                dict(role_id="Managed roles can not be assigned to users and thus won't work for muting people"))
        user = await Utils.get_user(message["user_id"])
        parts = {
            "role_name": Utils.escape_markdown(role.name),
            "role_id": role.id,
            "user": Utils.clean_user(user),
            "user_id": user.id
        }
        GearbotLogging.log_key(guild.id, f"config_mute_{t}_triggered", **parts)
        failed = []
        for channel in guild.text_channels:
            try:
                if text is None:
                    await channel.set_permissions(role, reason=Translator.translate(f'mute_{t}', guild.id),
                                                  overwrite=None)
                else:
                    await channel.set_permissions(role, reason=Translator.translate(f'mute_{t}', guild.id), **text)
            except Forbidden as ex:
                failed.append(channel.mention)
        for channel in guild.voice_channels:
            try:
                if voice is None:
                    await channel.set_permissions(role, reason=Translator.translate(f'mute_{t}', guild.id),
                                                  overwrite=None)
                else:
                    await channel.set_permissions(role, reason=Translator.translate(f'mute_{t}', guild.id), **voice)
            except Forbidden as ex:
                failed.append(Translator.translate('voice_channel', guild.id, channel=channel.name))

        await asyncio.sleep(1)  # delay logging so the channel overrides can get querried and logged
        GearbotLogging.log_key(
            guild.id,
            f"config_mute_{t}_complete",
            **parts
        )

        out = '\n'.join(failed)
        GearbotLogging.log_key(
            guild.id,
            f"config_mute_{t}_failed",
            **parts,
            count=len(failed),
            tag_on=None if len(failed) is 0 else f'```{out}```'
        )

    async def usernames_request(self, message):
        names = dict()
        todo = message["ids"].copy()
        # find all in the bot cache and back to
        for uid in message["ids"]:
            user = self.bot.get_user(int(uid))
            if user is not None:
                names[uid] = str(user)
                todo.remove(uid)
        # send those already, reset list
        if len(names) > 0:
            await self.send_to_dash("usernames", uid=message["uid"], names=names)
            names = dict()

        # check if we have any of these already in redis manually so we can do a batch, much faster then one by one
        pipeline = self.bot.redis_pool.pipeline()
        last_todo = todo.copy()
        for uid in todo:
            pipeline.hgetall(f"users:{uid}")
        results = await pipeline.execute()
        for result in results:
            if len(result) is not 0:
                uid = result["id"]
                names[uid] = f'{result["name"]}#{result["discriminator"]}'
                last_todo.remove(uid)
        if len(names) > 0:
            await self.send_to_dash("usernames", uid=message["uid"], names=names)

        for uid in last_todo:
            await self.send_to_dash("usernames", uid=message["uid"],
                                    names={uid: await Utils.username(uid, redis=False, clean=False)})

    # crowdin
    async def crowdin_webhook(self, message):
        code = message["language"]
        await Translator.update_lang(code)
        if (datetime.now() - self.last_update).seconds > 5 * 60:
            self.update_message = None
            self.to_log = dict()
        if code not in self.to_log:
            self.to_log[code] = 0
        self.to_log[code] += 1

        embed = Embed(
            color=Color(0x1183f6),
            timestamp=datetime.utcfromtimestamp(time.time()),
            description=f"**Live translation update summary!**\n" + '\n'.join(
                f"{Translator.LANG_NAMES[code]} : {count}" for code, count in self.to_log.items()
            )
        )
        if self.update_message is None:
            self.update_message = await Translator.get_translator_log_channel()(embed=embed)
        else:
            await self.update_message.edit(embed=embed)

        self.last_update = datetime.now()

    async def update(self, message):
        t = message["type"]
        if t == "update":
            await Update.update("whoever just pushed to master", self.bot)
        elif t == "upgrade":
            await Update.upgrade("whoever just pushed to master", self.bot)
        else:
            raise RuntimeError("UNKNOWN UPDATE MESSAGE, IS SOMEONE MESSING WITH IT?")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        for user in self.bot.dash_guild_users:
            member = guild.get_member(user)
            if member is not None:
                permission = DashUtils.get_guild_perms(member)
                if permission > 0:
                    await self.send_to_dash("guild_add", user_id=user, guilds={
                        str(guild.id): {
                            "id": str(guild.id),
                            "name": guild.name,
                            "permissions": permission,
                            "icon": guild.icon
                        }})

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        for user in self.bot.dash_guild_users:
            member = guild.get_member(user)
            if member is not None:
                permission = DashUtils.get_guild_perms(member)
                if permission > 0:
                    await self.send_to_dash("guild_remove", user_id=user, guild=str(guild.id))

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        for user in self.bot.dash_guild_users:
            member = after.get_member(user)
            if member is not None:
                old = DashUtils.get_guild_perms(member)
                new = DashUtils.get_guild_perms(member)
                if old != new:
                    await self._notify_user(member, old, new, after)
                elif before.name != after.name or before.icon != after.icon:
                    await self._notify_user(member, 0, 15, after)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if after.id in self.bot.dash_guild_users:
            old = DashUtils.get_guild_perms(before)
            new = DashUtils.get_guild_perms(after)
            await self._notify_user(after, old, new, before.guild)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        for user in self.bot.dash_guild_users:
            member = after.guild.get_member(user)
            if member is not None and after in member.roles:
                new = DashUtils.get_guild_perms(member)
                await self._notify_user(member, 0 if new is not 0 else 15, new, after.guild)

    @commands.Cog.listener()
    async def _notify_user(self, user, old, new, guild):
        if old != new:
            if new is not 0:
                await self.send_to_dash("guild_add", user_id=user.id, guilds={
                    str(guild.id): {
                        "id": str(guild.id),
                        "name": guild.name,
                        "permissions": new,
                        "icon": guild.icon
                    }
                })
        if new is 0 and old is not 0:
            await self.send_to_dash("guild_remove", user_id=user.id, guild=str(guild.id))


def setup(bot):
    bot.add_cog(DashLink(bot))
