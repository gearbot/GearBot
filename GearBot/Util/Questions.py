import asyncio
from collections import namedtuple

from discord import Embed, Reaction

from Util import MessageUtils

Option = namedtuple("Option", "emoji text handler")

async def ask(ctx, text, options, timeout=60):
    embed = Embed(color=0x68a910, description='\n'.join(f"{option.emoji} {option.text}" for option in options))
    message = await ctx.send(text, embed=embed)
    handlers = dict()
    for option in options:
        await message.add_reaction(option.emoji)
        handlers[str(option.emoji)] = option.handler
    def check(reaction):
        return reaction.user_id == ctx.message.author.id and str(reaction.emoji) in handlers.keys() and reaction.message_id == message.id
    try:
        reaction = await ctx.bot.wait_for('raw_reaction_add', timeout=timeout, check=check)
    except asyncio.TimeoutError:
        await MessageUtils.send_to(ctx, "NO", "confirmation_timeout", timeout=30)
        return
    else:
        await handlers[str(reaction.emoji)]()
    finally:
        await message.delete()