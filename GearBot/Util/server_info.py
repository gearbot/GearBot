import time
from datetime import datetime

import discord

from Util import Translator, Emoji


def server_info(guild, request_guild=None):
    guild_features = ", ".join(guild.features)
    if guild_features == "":
        guild_features = None
    guild_made = guild.created_at.strftime("%d-%m-%Y")
    embed = discord.Embed(color=guild.roles[-1].color, timestamp=datetime.fromtimestamp(time.time()))
    embed.set_thumbnail(url=guild.icon_url)
    embed.add_field(name=Translator.translate('server_name', request_guild), value=guild.name, inline=True)
    embed.add_field(name=Translator.translate('id', request_guild), value=guild.id, inline=True)
    embed.add_field(name=Translator.translate('owner', request_guild), value=guild.owner, inline=True)
    embed.add_field(name=Translator.translate('members', request_guild), value=guild.member_count, inline=True)
    embed.add_field(name=Translator.translate('text_channels', request_guild), value=str(len(guild.text_channels)),
                    inline=True)
    embed.add_field(name=Translator.translate('voice_channels', request_guild), value=str(len(guild.voice_channels)),
                    inline=True)
    embed.add_field(name=Translator.translate('total_channel', request_guild),
                    value=str(len(guild.text_channels) + len(guild.voice_channels)),
                    inline=True)
    embed.add_field(name=Translator.translate('created_at', request_guild),
                    value=f"{guild_made} ({(datetime.fromtimestamp(time.time()) - guild.created_at).days} days ago)",
                    inline=True)
    embed.add_field(name=Translator.translate('vip_features', request_guild), value=guild_features, inline=True)
    if guild.icon_url != "":
        embed.add_field(name=Translator.translate('server_icon', request_guild),
                        value=f"[{Translator.translate('server_icon', request_guild)}]({guild.icon_url})", inline=True)
    roles = ", ".join(role.name for role in guild.roles)
    embed.add_field(name=Translator.translate('all_roles', request_guild),
                    value=roles if len(roles) < 1024 else f"{len(guild.roles)} roles", inline=True)
    if guild.emojis:
        emoji = "".join(str(e) for e in guild.emojis)
        embed.add_field(name=Translator.translate('emoji', request_guild),
                        value=emoji if len(emoji) < 1024 else f"{len(guild.emojis)} emoji")
    statuses = dict(online=0, idle=0, dnd=0, offline=0)
    for m in guild.members:
        statuses[str(m.status)] += 1
    embed.add_field(name=Translator.translate('member_statuses', request_guild), value="\n".join(f"{Emoji.get_chat_emoji(status.upper())} {Translator.translate(status, request_guild)}: {count}" for status, count in statuses.items()))
    if guild.splash_url != "":
        embed.set_image(url=guild.splash_url)
    return embed


def time_difference(begin, end, location):
    diff = begin - end
    minutes, seconds = divmod(diff.days * 86400 + diff.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return (Translator.translate('days', location, days=diff.days)) if diff.days > 0 else Translator.translate('hours',
                                                                                                               location,
                                                                                                               hours=hours,
                                                                                                               minutes=minutes)