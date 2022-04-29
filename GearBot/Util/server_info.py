import time
import datetime

import disnake
from disnake import utils

from Util import Translator, Emoji, Utils, Configuration


def server_info_embed(guild, request_guild=None):
    guild_features = ", ".join(guild.features).title().replace("_", " ")
    if guild_features == "":
        guild_features = None
    guild_made = guild.created_at
    embed = disnake.Embed(color=guild.roles[-1].color, timestamp=datetime.datetime.utcfromtimestamp(time.time()).replace(tzinfo=datetime.timezone.utc))
    if guild.icon is not None:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name=Translator.translate('server_name', request_guild), value=guild.name, inline=True)
    embed.add_field(name=Translator.translate('id', request_guild), value=guild.id, inline=True)
    embed.add_field(name=Translator.translate('owner', request_guild), value=guild.owner, inline=True)
    embed.add_field(name=Translator.translate('members', request_guild), value=guild.member_count, inline=True)

    embed.add_field(
        name=Translator.translate('channels', request_guild),
        value=f"{Emoji.get_chat_emoji('CATEGORY')} {Translator.translate('categories', request_guild)}: {str(len(guild.categories))}\n"
              f"{Emoji.get_chat_emoji('CHANNEL')} {Translator.translate('text_channels', request_guild)}: {str(len(guild.text_channels))}\n"
              f"{Emoji.get_chat_emoji('VOICE')} {Translator.translate('voice_channels', request_guild)}: {str(len(guild.voice_channels))}\n"
              f"{Translator.translate('total_channel', request_guild)}: {str(len(guild.text_channels) + len(guild.voice_channels))}",
        inline=True
    )
    embed.add_field(
        name=Translator.translate('created_at', request_guild),
        value=f"{utils.format_dt(guild_made, 'F')} ({utils.format_dt(guild_made, 'R')})",
        inline=True
    )
    embed.add_field(
        name=Translator.translate('vip_features', request_guild),
        value=guild_features,
        inline=True
    )
    if guild.icon is not None:
        embed.add_field(
            name=Translator.translate('server_icon', request_guild),
            value=f"[{Translator.translate('server_icon', request_guild)}]({guild.icon.url})",
            inline=True
        )

    roles = ", ".join(role.name for role in guild.roles)
    embed.add_field(
        name=Translator.translate('all_roles', request_guild),
        value=roles if len(roles) < 1024 else f"{len(guild.roles)} roles",
        inline=False
    )

    if guild.emojis:
        emoji = "".join(str(e) for e in guild.emojis)
        embed.add_field(
            name=Translator.translate('emoji', request_guild),
            value=emoji if len(emoji) < 1024 else f"{len(guild.emojis)} emoji"
        )

    if guild.splash is not None:
        embed.set_image(url=guild.splash.url)
    if guild.banner is not None:
        embed.set_image(url=guild.banner.url)

    return embed


def server_info_raw(bot, guild):
    statuses = dict(online=0, idle=0, dnd=0, offline=0)
    for m in guild.members:
        statuses[str(m.status)] += 1
    extra = dict()
    for g in Configuration.get_var(guild.id, "SERVER_LINKS"):
        extra.update(**{str(k): v for k, v in get_server_channels(bot.get_guild(g)).items()})
    server_info = dict(
        name=guild.name,
        id=str(guild.id),  # send as string, js can't deal with it otherwise
        icon=str(guild.icon),
        owner={
            "id": str(guild.owner.id),
            "name": Utils.clean_user(guild.owner)
        },
        members=guild.member_count,
        text_channels=get_server_channels(guild),
        additional_text_channels=extra,
        voice_channels=len(guild.voice_channels),
        creation_date=guild.created_at.strftime("%d-%m-%Y"),  # TODO: maybe date and have the client do the displaying?
        age_days=(datetime.datetime.fromtimestamp(time.time()) - guild.created_at).days,
        vip_features=guild.features,
        role_list={
            r.id: {
                "id": str(r.id),
                "name": r.name,
                "color": '#{:0>6x}'.format(r.color.value),
                "members": len(r.members),
                "is_admin": r.permissions.administrator,
                "is_mod": r.permissions.ban_members,
                "can_be_self_role": not r.managed and guild.me.top_role > r and r.id != guild.id,
            } for r in guild.roles},
        emojis=[
            {
                "id": str(e.id),
                "name": e.name
            }
            for e in guild.emojis],
        member_statuses=statuses
    )

    return server_info


def get_server_channels(guild):
    return {
        str(c.id): {
            'name': c.name,
            'can_log': c.permissions_for(c.guild.me).send_messages and c.permissions_for(
                c.guild.me).attach_files and c.permissions_for(c.guild.me).embed_links
        } for c in guild.text_channels
    }


def time_difference(begin, end, location):
    diff = begin - end
    minutes, seconds = divmod(diff.days * 86400 + diff.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if diff.days > 0:
        return Translator.translate("days", location, amount=diff.days)
    else:
        return Translator.translate(
            "hours",
            location,
            hours=hours,
            minutes=minutes
        )
