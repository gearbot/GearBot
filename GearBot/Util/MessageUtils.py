from database.DatabaseConnector import LoggedMessage, LoggedAttachment


def is_cache_enabled(bot):
    return bot.redis_pool is not None

async def get_message(bot, message_id, bypass_cache=False):
    if is_cache_enabled(bot) and not bypass_cache:
        pass
    pass

async def insert_message(bot, message):
    if is_cache_enabled(bot):
        pipe = bot.redis_pool.pipeline()
        pipe.hmset_dict(message.id, author=message.author.id, content=message.content,
                         channel=message.channel.id, server=message.guild.id)
        pipe.expire(message.id, 5*60)
        await pipe.execute()
    LoggedMessage.create(messageid=message.id, author=message.author.id, content=message.content,
                         channel=message.channel.id, server=message.guild.id)
    for a in message.attachments:
        LoggedAttachment.create(id=a.id, url=a.url, isImage=(a.width is not None or a.width is 0),
                                messageid=message.id)

async def update_message(bot, message):
    pass

