import asyncio

from discord import Forbidden, NotFound, Embed, Colour

from Util import Emoji, Pages, InfractionUtils, Selfroles, Translator, Configuration, MessageUtils, Utils


async def paged(bot, message, user_id, reaction, **kwargs):
    user = message.channel.guild.get_member(user_id)
    if user is None:
        await remove_reaction(message, reaction, await bot.fetch_user(user_id))
        return
    left = Emoji.get_chat_emoji('LEFT')
    right = Emoji.get_chat_emoji('RIGHT')
    refresh = Emoji.get_chat_emoji('REFRESH')
    r2 = "🔁"
    if str(reaction) not in [left, right, refresh, r2]:
        return kwargs
    action = "REFRESH"
    if str(reaction) == left:
        action = "PREV"
    elif str(reaction) == right:
        action = "NEXT"
    bot.loop.create_task(remove_reaction(message, reaction, user))
    return await Pages.update(bot, message, action, user_id, **kwargs)


async def self_roles(bot, message, user_id, reaction, **kwargs):
    user = message.channel.guild.get_member(user_id)
    if user is None:
        await remove_reaction(message, reaction, await bot.fetch_user(user_id))
        return kwargs
    bot.loop.create_task(remove_reaction(message, reaction, user))
    left = Emoji.get_chat_emoji('LEFT')
    right = Emoji.get_chat_emoji('RIGHT')
    refresh = Emoji.get_chat_emoji('REFRESH')
    r2 = "🔁"
    page_num = int(kwargs.get("page_num", 0))
    add = reaction not in [left, right, refresh, r2]
    if str(reaction) == left:
        page_num -= 1
        add = False
    elif str(reaction) == right:
        page_num += 1
        add = False
    elif str(reaction) in [refresh, r2]:
        add = False
    if not add:
        return kwargs
    for i in range(10):
        if str(reaction) == str(Emoji.get_emoji(str(i+1))):
            roles = Configuration.get_var(message.guild.id, "SELF_ROLES")
            role = message.channel.guild.get_role(roles[page_num*10 + i])
            if role is None:
                await Selfroles.validate_self_roles(bot, message.channel.guild)
                return
            add_role = role not in user.roles
            try:
                await (user.add_roles if add_role else user.remove_roles)(role)
            except Forbidden:
                if message.channel.permissions_for(message.channel.guild.me).send_messages:
                    await MessageUtils.send_to(message.channel, "NO", "mute_role_to_high")
                    return kwargs
            else:
                if message.channel.permissions_for(message.channel.guild.me).send_messages:
                    await MessageUtils.send_to(message.channel, "YES", "role_joined" if add_role else "role_left", role_name=await Utils.clean(role.name), delete_after=10)
                    bot.loop.create_task(remove_reaction(message, reaction, user))
                    return kwargs


    if add:
        return kwargs
    pages = Selfroles.gen_role_pages(message.channel.guild)

    if str(reaction) in [refresh, r2]:
        if not message.channel.guild.me.guild_permissions.manage_messages:
            return kwargs
        await message.clear_reactions()
        await asyncio.sleep(0.2)
    if page_num >= len(pages):
        page_num = 0
    elif page_num < 0:
        page_num = len(pages) - 1
    kwargs["page_num"] = page_num
    embed = Embed(title=Translator.translate("assignable_roles", message.channel, server_name=message.channel.guild.name, page_num=page_num+1,
                                             page_count=len(pages)), colour=Colour(0xbffdd), description=pages[page_num])
    await message.edit(embed=embed)
    await Selfroles.update_reactions(message, pages[page_num], len(pages) > 1)
    bot.loop.create_task(bot.redis_pool.expire(f"self_role:{message.channel.guild.id}", int(kwargs.get("duration", 60 * 60 * 24 * 7))))
    return kwargs

async def inf_search(bot, message, user_id, reaction, **kwargs):
    user = message.channel.guild.get_member(user_id)
    left = Emoji.get_chat_emoji('LEFT')
    right = Emoji.get_chat_emoji('RIGHT')
    refresh = Emoji.get_chat_emoji('REFRESH')
    r2 = "🔁"
    if str(reaction) not in [left, right, refresh, r2]:
        return kwargs
    page_num = int(kwargs.get("page_num", 0))
    if str(reaction) == left:
        page_num -= 1
    elif str(reaction) == right:
        page_num += 1
    if user is not None:
        bot.loop.create_task(remove_reaction(message, reaction, user))
    return await InfractionUtils.inf_update(message, kwargs.get("query", None), kwargs.get("fields", "").split("-"), kwargs.get("amount", 100), page_num)

async def register(bot, message_id, channel_id, type, pipe=None, **kwargs):
    if pipe is None:
        pipe = bot.redis_pool.pipeline()
    key = f"reactor:{message_id}"
    pipe.hmset_dict(key, message_id=message_id, channel_id=channel_id, type=type, **kwargs)
    pipe.expire(key, kwargs.get("duration", 60*60*24))
    await pipe.execute()


handlers = {
    "paged": paged,
    "self_role":  self_roles,
    "inf_search": inf_search
}

async def on_reaction(bot, message_id, channel_id, user_id, reaction):
    if user_id == bot.user.id:
        return
    key = f"reactor:{message_id}"
    info = await bot.redis_pool.hgetall(key)
    if len(info) >= 3:
        type = info["type"]
        del info["type"]

        # got to love races
        channel = bot.get_channel(channel_id)
        if channel is None:
            # let's clean a bit while we're here anyways
            await bot.redis_pool.unlink(key)
            return
        try:
            message = await channel.fetch_message(message_id)
        except (NotFound, Forbidden):
            # yay for more races and weird permission setups
            await bot.redis_pool.unlink(key)
        else:
            new_info = await handlers[type](bot, message, user_id, reaction, **info)
            if new_info is not None:
                pipeline = bot.redis_pool.pipeline()
                pipeline.hmset_dict(key, **new_info)
                pipeline.expire(key, int(info.get("duration", 60*60*24)))
                pipeline.expire(f"inf_track:{channel.guild.id}", 60*60*24)
                await pipeline.execute()


async def remove_reaction(message, reaction, user):
    if user is None:
        return
    try:
        await message.remove_reaction(reaction, user)
    except Forbidden:
        pass