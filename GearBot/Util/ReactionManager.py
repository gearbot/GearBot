import asyncio

from disnake import Forbidden, NotFound, Embed, Colour, Object

from Util import Emoji, Pages, InfractionUtils, Selfroles, Translator, Configuration, MessageUtils, Utils
from views.SelfRole import SelfRoleView


async def paged(bot, message, user_id, reaction, **kwargs):
    user = await Utils.get_member(bot, message.channel.guild, user_id)
    if user is None:
        await remove_reaction(message, reaction, Object(user_id))
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
    v = SelfRoleView(guild=message.guild, page=0)
    await message.edit(
        Translator.translate("assignable_roles", message.guild, server_name=message.guild.name, page_num=1,
                             page_count=v.pages), view=v, embed=None)
    await unregister(bot, message.id)
    try:
        await message.clear_reactions()
    except Exception as e:
        pass


async def inf_search(bot, message, user_id, reaction, **kwargs):
    user = await Utils.get_member(bot, message.channel.guild, user_id)
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
    # return await InfractionUtils.inf_update(message, kwargs.get("query", None), kwargs.get("fields", "").split("-"), kwargs.get("amount", 100), page_num)


async def register(bot, message_id, channel_id, type, pipe=None, **kwargs):
    if pipe is None:
        pipe = bot.redis_pool.pipeline()
    key = f"reactor:{message_id}"
    pipe.hmset_dict(key, message_id=message_id, channel_id=channel_id, type=type, **kwargs)
    pipe.expire(key, kwargs.get("duration", 60 * 60 * 8))
    await pipe.execute()

async def unregister(bot, message_id):
    await bot.redis_pool.unlink(f"reactor:{message_id}")


handlers = {
    "paged": paged,
    "self_role": self_roles,
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
                pipeline.expire(key, int(info.get("duration", 60 * 60 * 24)))
                pipeline.expire(f"inf_track:{channel.guild.id}", 60 * 60 * 24)
                await pipeline.execute()


async def remove_reaction(message, reaction, user):
    if user is None:
        return
    try:
        await message.remove_reaction(reaction, user)
    except (Forbidden, NotFound):
        pass
