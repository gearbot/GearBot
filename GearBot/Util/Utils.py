import asyncio
import json
import os
import subprocess
from collections import namedtuple, OrderedDict
import datetime
from json import JSONDecodeError
from subprocess import Popen
from pyseeyou import format

import discord
import math
from discord import NotFound, DiscordException

from Util import GearbotLogging, Translator, Emoji, Configuration, MessageUtils
from Util.Matchers import ROLE_ID_MATCHER, CHANNEL_ID_MATCHER, ID_MATCHER, EMOJI_MATCHER, URL_MATCHER, ID_NUMBER_MATCHER
from database.DatabaseConnector import Infraction

BOT = None


def initialize(actual_bot):
    global BOT
    BOT = actual_bot


def fetch_from_disk(filename, alternative=None):
    try:
        with open(f"{filename}.json", encoding="UTF-8") as file:
            return json.load(file)
    except FileNotFoundError:
        GearbotLogging.info(f"Tried to load {filename}.json but couldn't find it on disk")
        if alternative is not None:
            return fetch_from_disk(alternative)
    return dict()


def save_to_disk(filename, dict):
    with open(f"{filename}.json", "w", encoding="UTF-8") as file:
        json.dump(dict, file, indent=4, skipkeys=True, sort_keys=True)


async def cleanExit(bot, trigger):
    await GearbotLogging.bot_log(f"Shutdown triggered by {trigger}.")
    await bot.logout()
    await bot.close()
    bot.aiosession.close()


def trim_message(message, limit):
    if len(message) < limit - 4:
        return message
    return f"{message[:limit - 4]}..."


async def empty_list(ctx, action):
    try:
        message = await ctx.send(
            f"{Translator.translate('m_nobody', ctx, action=action)} {Emoji.get_chat_emoji('THINK')}")
        await asyncio.sleep(3)
        message2 = await ctx.send(f"{Translator.translate('m_nobody_2', ctx)} {Emoji.get_chat_emoji('WINK')}")
        await asyncio.sleep(3)
        await message.edit(content=Translator.translate('intimidation', ctx))
        await message2.delete()
    except DiscordException:
        pass


replacements = {
    "`": "ˋ"
}


def replace_lookalikes(text):
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


async def clean(text, guild: discord.Guild = None, markdown=True, links=True, emoji=True, lookalikes=True):
    text = str(text)

    if guild is not None:
        # resolve user mentions
        for uid in set(ID_MATCHER.findall(text)):
            name = "@" + await username(int(uid), False, False)
            text = text.replace(f"<@{uid}>", name)
            text = text.replace(f"<@!{uid}>", name)

        # resolve role mentions
        for uid in set(ROLE_ID_MATCHER.findall(text)):
            role = discord.utils.get(guild.roles, id=int(uid))
            if role is None:
                name = "@UNKNOWN ROLE"
            else:
                name = "@" + role.name
            text = text.replace(f"<@&{uid}>", name)

        # resolve channel names
        for uid in set(CHANNEL_ID_MATCHER.findall(text)):
            channel = guild.get_channel(uid)
            if channel is None:
                name = "#UNKNOWN CHANNEL"
            else:
                name = "#" + channel.name
            text = text.replace(f"<@#{uid}>", name)

        # re-assemble emoji so such a way that they don't turn into twermoji

    urls = set(URL_MATCHER.findall(text))

    if lookalikes:
        text = replace_lookalikes(text)

    if markdown:
        text = escape_markdown(text)
    else:
        text = text.replace("@", "@\u200b").replace("**", "*​*").replace("``", "`​`")

    if emoji:
        for e in set(EMOJI_MATCHER.findall(text)):
            a, b, c = zip(e)
            text = text.replace(f"<{a[0]}:{b[0]}:{c[0]}>", f"<{a[0]}\\:{b[0]}\\:{c[0]}>")

    if links:
        # find urls last so the < escaping doesn't break it
        for url in urls:
            text = text.replace(escape_markdown(url), f"<{url}>")

    return text


def escape_markdown(text):
    text = str(text)
    for c in ["\\", "*", "_", "~", "|", "{", ">"]:
        text = text.replace(c, f"\\{c}")
    return text.replace("@", "@\u200b")


def clean_name(text):
    if text is None:
        return None
    return str(text).replace("@", "@\u200b").replace("**", "*\u200b*").replace("``", "`\u200b`")


known_invalid_users = []
user_cache = OrderedDict()


async def username(uid, fetch=True, clean=True):
    user = await get_user(uid, fetch)
    if user is None:
        return "UNKNOWN USER"
    if clean:
        return clean_user(user)
    else:
        return f"{user.name}#{user.discriminator}"


UserClass = namedtuple("UserClass", "name id discriminator bot avatar created_at mention")
UserAvatar = namedtuple("UserAvatar", "url is_animated")


def t():
    return True


def f():
    return False


async def get_user(uid, fetch=True):
    if uid is None or not isinstance(uid, int):
        return None
    if uid > 9223372036854775807:
        return None
    user = BOT.get_user(uid)
    if user is None:
        if uid in known_invalid_users:
            return None

        if BOT.redis_pool is not None:
            userCacheInfo = await BOT.redis_pool.hgetall(f"users:{uid}")

            if len(userCacheInfo) == 8:  # It existed in the Redis cache, check length cause sometimes somehow things are missing, somehow
                userFormed = UserClass(
                    userCacheInfo["name"],
                    userCacheInfo["id"],
                    userCacheInfo["discriminator"],
                    userCacheInfo["bot"] == "1",
                    UserAvatar(
                        userCacheInfo["avatar_url"],
                        True if bool(userCacheInfo["is_avatar_animated"]) == "1" else False
                    ),
                    datetime.datetime.utcfromtimestamp(float(userCacheInfo["created_at"])).replace(
                        tzinfo=datetime.timezone.utc),
                    userCacheInfo["mention"]
                )

                return userFormed
            if fetch:
                try:
                    user = await BOT.fetch_user(uid)
                    pipeline = BOT.redis_pool.pipeline()
                    pipeline.hmset_dict(f"users:{uid}",
                                        name=user.name,
                                        id=user.id,
                                        discriminator=user.discriminator,
                                        bot=int(user.bot),
                                        avatar_url=str(user.avatar.url),
                                        created_at=user.created_at.timestamp(),
                                        is_avatar_animated=int(user.avatar.is_animated()),
                                        mention=user.mention
                                        )

                    pipeline.expire(f"users:{uid}", 3000)  # 5 minute cache life

                    BOT.loop.create_task(pipeline.execute())

                except NotFound:
                    known_invalid_users.append(uid)
                    return None
        else:  # No Redis, using the dict method instead
            if uid in user_cache:
                return user_cache[uid]
            if fetch:
                try:
                    user = await BOT.fetch_user(uid)
                    if len(user_cache) >= 10:  # Limit the cache size to the most recent 10
                        user_cache.popitem()
                    user_cache[uid] = user
                except NotFound:
                    known_invalid_users.append(uid)
                    return None
    return user


def clean_user(user):
    if user is None:
        return "UNKNOWN USER"
    return f"{escape_markdown(replace_lookalikes(user.name))}#{user.discriminator}"


def username_from_user(user):
    if user is None:
        return "UNKNOWN USER"
    return user.name


def pad(text, length, char=' '):
    return f"{text}{char * (length - len(text))}"


async def execute(command):
    p = Popen(command, cwd=os.getcwd(), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while p.poll() is None:
        await asyncio.sleep(1)
    out, error = p.communicate()
    return p.returncode, out.decode('utf-8').strip(), error.decode('utf-8').strip()


def find_key(data, wanted):
    for k, v in data.items():
        if v == wanted:
            return k


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


async def get_commit():
    _, out, __ = await execute('git rev-parse --short HEAD')
    return out


def to_pretty_time(seconds, guild_id):
    seconds = max(round(seconds, 2), 0)
    partcount = 0
    parts = {
        'weeks': 60 * 60 * 24 * 7,
        'days': 60 * 60 * 24,
        'hours_solo': 60 * 60,
        'minutes': 60,
        'seconds': 1
    }
    duration = ""

    if seconds < 1:
        return Translator.translate("seconds", guild_id, amount=seconds)

    for k, v in parts.items():
        if seconds / v >= 1:
            amount = math.floor(seconds / v)
            seconds -= amount * v
            if partcount == 1:
                duration += ", "
            duration += " " + Translator.translate(k, guild_id, amount=amount)
        if seconds == 0:
            break
    return duration.strip()


def assemble_attachment(channel, aid, name):
    return f"https://media.discordapp.net/attachments/{channel}/{aid}/{name}"


def assemble_jumplink(server, channel, message):
    return f"https://canary.discord.com/channels/{server}/{channel}/{message}"


async def get_member(bot, guild, user_id, fetch_if_missing=False):
    member = guild.get_member(user_id)
    if member is None and fetch_if_missing:
        try:
            member = await guild.fetch_member(user_id)
        except DiscordException:
            return None
    return member


async def send_infraction(bot, user, guild, emoji, type, reason, **kwargs):
    if await get_member(bot, guild, user.id) is None:
        return
    try:
        override = Configuration.get_var(guild.id, "INFRACTIONS", type.upper())
        kwargs.update(
            reason=reason,
            server=guild.name,
            guild_id=guild.id
        )
        if override is not None:
            message = f"{Emoji.get_chat_emoji(emoji)} {format(override, kwargs, Configuration.get_var(guild.id, 'GENERAL', 'LANG'))}```{reason}```"
        else:
            message = f"{Emoji.get_chat_emoji(emoji)} {Translator.translate(f'{type.lower()}_dm', guild.id, **kwargs)}```{reason}```"
        parts = message.split("```")
        out = ""
        wrap = False
        while len(parts) > 0:
            temp = parts.pop(0)
            added = 6 if wrap else 0
            chars = "```" if wrap else ""
            if (len(out) + len(temp) + added) > 2000:
                await user.send(out)
                temp = ""
            out = f"{out}{chars}{temp}{chars}"
            wrap = not wrap
        if len(out) > 0:
            await user.send(out)
    except (discord.HTTPException, AttributeError):
        GearbotLogging.log_key(guild.id, f'{type}_could_not_dm', user=clean_user(user), userid=user.id)


def enrich_reason(ctx, reason):
    if reason != "" and len(ctx.message.attachments) > 0:
        reason += " " + ",".join(
            [assemble_attachment(ctx.message.channel.id, attachment.id, attachment.filename) for attachment in
             ctx.message.attachments])
    if reason == '':
        reason = Translator.translate('no_reason', ctx)
    if len(reason) > 1800:
        from Util.Converters import TranslatedBadArgument
        raise TranslatedBadArgument('reason_too_long', ctx)
    return reason

async def get_user_ids(text):
    parts = set()
    for p in set(ID_NUMBER_MATCHER.findall(text)):
        try:
            id = int(p)
            if id not in parts:
                if await get_user(id) is not None:
                    parts.add(p)
        except ValueError:
            pass
    return parts


async def generate_userinfo_embed(user, member, guild, requested_by):
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    embed = discord.Embed(color=member.top_role.color if member is not None else 0x00cea2,
                          timestamp=now)
    embed.set_thumbnail(url=user.avatar.url)
    embed.set_footer(text=Translator.translate('requested_by', guild, user=requested_by.name),
                     icon_url=requested_by.avatar.url)
    embed.add_field(name=Translator.translate('name', guild),
                    value=escape_markdown(f"{user.name}#{user.discriminator}"), inline=True)
    embed.add_field(name=Translator.translate('id', guild), value=user.id, inline=True)
    embed.add_field(name=Translator.translate('bot_account', guild), value=user.bot, inline=True)
    embed.add_field(name=Translator.translate('animated_avatar', guild), value=user.avatar.is_animated(), inline=True)
    embed.add_field(name=Translator.translate('avatar_url', guild),
                    value=f"[{Translator.translate('avatar_url', guild)}]({user.avatar.url})")
    embed.add_field(name=Translator.translate("profile", guild), value=user.mention)
    if member is not None:
        embed.add_field(name=Translator.translate('nickname', guild), value=escape_markdown(member.nick),
                        inline=True)

        role_list = [role.mention for role in reversed(member.roles) if role is not guild.default_role]
        if len(role_list) > 60:
            embed.add_field(name=Translator.translate('all_roles', guild),
                            value=Translator.translate('too_many_many_roles', guild), inline=False)
        elif len(role_list) > 40:
            embed.add_field(name=Translator.translate('all_roles', guild),
                            value=Translator.translate('too_many_roles', guild), inline=False)
        elif len(role_list) > 0:
            embed.add_field(name=Translator.translate('all_roles', guild), value=" ".join(role_list), inline=False)
        else:
            embed.add_field(name=Translator.translate('all_roles', guild),
                            value=Translator.translate("no_roles", guild), inline=False)

        embed.add_field(name=Translator.translate('joined_at', guild),
                        value=f"{(now - member.joined_at).days} days ago (``{member.joined_at}``)",
                        inline=True)
    embed.add_field(name=Translator.translate('account_created_at', guild),
                    value=f"{(now - user.created_at).days} days ago (``{user.created_at}``)",
                    inline=True)
    infs = ""
    if Configuration.get_master_var("global_inf_counter", True):
        infractions = await Infraction.filter(user_id=user.id, type__not="Note")
        il = len(infractions)
        seen = []
        ild = 0
        for i in infractions:
            if i.guild_id not in seen:
                seen.append(i.guild_id)
            ild += 1
        emoji = "SINISTER" if il >= 2 else "INNOCENT"
        infs += MessageUtils.assemble(guild, emoji, "total_infractions", total=il, servers=ild) + "\n"

    infractions = await Infraction.filter(user_id=user.id, guild_id=guild.id, type__not="Note")
    emoji = "SINISTER" if len(infractions) >= 2 else "INNOCENT"
    embed.add_field(name=Translator.translate("infractions", guild),
                value=infs + MessageUtils.assemble(guild, emoji, "guild_infractions", count=len(infractions)))
    return embed
