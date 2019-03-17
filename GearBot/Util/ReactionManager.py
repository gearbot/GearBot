from discord import Forbidden, NotFound

from Util import Emoji, Pages, InfractionUtils


async def paged(bot, message, user_id, reaction, **kwargs):
    user = message.channel.guild.get_member(user_id)
    if reaction == str(Emoji.get_emoji('LEFT')):
        new_info = await Pages.update(bot, message, "PREV", user_id, **kwargs)
        try:
            await message.remove_reaction(Emoji.get_emoji('LEFT'), user)
        except Forbidden:
            pass
        return new_info
    elif reaction == str(Emoji.get_emoji('RIGHT')):
        new_info = await Pages.update(bot, message, "NEXT", user_id, **kwargs)
        try:
            await message.remove_reaction(Emoji.get_emoji('RIGHT'), user)
        except Forbidden:
            pass
        return new_info

async def self_roles():
    pass

async def inf_search(bot, message, user_id, reaction, **kwargs):
    user = message.channel.guild.get_member(user_id)
    page_num = int(kwargs.get("page_num", 0))
    if reaction == str(Emoji.get_emoji('LEFT')):
        page_num -= 1
        bot.loop.create_task(remove_reaction(message, 'LEFT', user))
    elif reaction == str(Emoji.get_emoji('RIGHT')):
        page_num += 1
        bot.loop.create_task(remove_reaction(message, 'RIGHT', user))
    return await InfractionUtils.inf_update(message, kwargs.get("query", None), kwargs.get("fields", "").split("-"), kwargs.get("amount", 100), page_num)

async def register(bot, message_id, channel_id, type, **kwargs):
    pipe = bot.redis_pool.pipeline()
    key = f"reactor:{message_id}"
    pipe.hmset_dict(key, message_id=message_id, channel_id=channel_id, type=type, **kwargs)
    pipe.expire(key, kwargs.get("duration", 60*60*24))
    await pipe.execute()


handlers = {
    "paged": paged,
    "self_roles":  self_roles,
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
            message = await channel.get_message(message_id)
        except (NotFound, Forbidden):
            # yay for more races and weird permission setups
            await bot.redis_pool.unlink(key)
        else:
            new_info = await handlers[type](bot, message, user_id, reaction, **info)
            pipeline = bot.redis_pool.pipeline()
            pipeline.hmset_dict(key, **new_info)
            pipeline.expire(key, info.get("duration", 60*60*24))
            await pipeline.execute()


async def remove_reaction(message, reaction, user):
    try:
        await message.remove_reaction(Emoji.get_emoji(reaction), user)
    except Forbidden:
        pass