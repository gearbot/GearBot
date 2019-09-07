from discord import Embed, Colour

from Util import Configuration, Pages, Translator, ReactionManager, Emoji


def validate_self_roles(bot, guild):
    roles = Configuration.get_var(guild.id, "ROLES", "SELF_ROLES")
    to_remove = set(role for role in roles if guild.get_role(role) is None)
    if len(to_remove) > 0:
        Configuration.set_var(guild.id, "ROLES", "SELF_ROLES", set(roles) - to_remove)
        bot.dispatch("self_roles_update", guild.id)

async def create_self_roles(bot, ctx):
    # create and send
    pages = gen_role_pages(ctx.guild)
    embed = Embed(title=Translator.translate("assignable_roles", ctx, server_name=ctx.guild.name, page_num=1,
                                   page_count=len(pages)), colour=Colour(0xbffdd), description=pages[0])
    message = await ctx.send(embed=embed)
    # track in redis
    pipe = bot.redis_pool.pipeline()
    pipe.sadd(f"self_role:{ctx.guild.id}", message.id)
    pipe.expire(f"self_role:{ctx.guild.id}", 60*60*24*7)
    bot.loop.create_task(ReactionManager.register(bot, message.id, ctx.channel.id, "self_role", duration=60*60*24*7, pipe=pipe))
    bot.loop.create_task(update_reactions(message, pages[0], len(pages) > 1))

    # cleanup
    bot.loop.create_task(self_cleaner(bot, ctx.guild.id))


async def update_reactions(message, page, has_multiple):
    left = Emoji.get_emoji("LEFT")
    if has_multiple and not any(left == r.emoji and r.me for r in message.reactions):
        await message.add_reaction(left)
    # add numbered reactions
    needed = int(len(page.splitlines()) / 2)
    added = False
    for i in range(10):
        reaction = Emoji.get_emoji(str(i+1))
        if i < needed:
            added = True
            await message.add_reaction(reaction)
        elif any(reaction == r.emoji and r.me for r in message.reactions):
            await message.remove_reaction(reaction, message.channel.guild.me)

    right = Emoji.get_emoji("RIGHT")
    has_right = any(right == r.emoji and r.me for r in message.reactions)
    if added and has_right:
        await message.remove_reaction(right, message.channel.guild.me)
        has_right = False
    if not has_right and has_multiple:
        await message.add_reaction(right)

    has_left = any(left == r.emoji and r.me for r in message.reactions)
    if has_left and has_multiple:
        await message.remove_reaction(left, message.channel.guild.me)



async def self_cleaner(bot, guild_id):
    pipeline = bot.redis_pool.pipeline()
    key = f"self_role:{guild_id}"
    reactors = await bot.redis_pool.smembers(key)
    for reactor in reactors:
        pipeline.hget(f"reactor:{reactor}", "channel_id")
    bits = await pipeline.execute()
    out = list()
    pipeline = bot.redis_pool.pipeline()
    for i in range(len(reactors)):
        if bits[i] is None:
            pipeline.srem(key, reactors[i])
        else:
            out.append((reactors[i], int(bits[i])))
    bot.loop.create_task(pipeline.execute())
    return out


def gen_role_pages(guild):
    roles = Configuration.get_var(guild.id, "ROLES", "SELF_ROLES")
    current_roles = ""
    count = 1
    for role in roles:
        current_roles += f"{count}) <@&{role}>\n\n"
        count += 1
        if count > 10:
            count = 1
    return Pages.paginate(current_roles, max_lines=20)
