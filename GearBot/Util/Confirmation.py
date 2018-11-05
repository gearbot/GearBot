import asyncio

import discord
from discord import utils
from discord.ext import commands

from Util import GearbotLogging

yesID = 465582004260569088
noID = 465582003874693130
yes = None
no = None


def on_ready(bot):
    global yes, no
    yes = utils.get(bot.emojis, id=yesID)
    no = utils.get(bot.emojis, id=noID)


async def confirm(ctx: commands.Context, text, timeout=30, on_yes=None, on_no=None, delete=True):
    bot = ctx.bot
    message: discord.Message = await ctx.send(text)
    await message.add_reaction(yes)
    await message.add_reaction(no)

    def check(reaction: discord.Reaction, user):
        return user == ctx.message.author and reaction.emoji in (yes, no) and reaction.message.id == message.id

    try:
        task = ctx.bot.loop.create_task(ctx.bot.wait_for('reaction_add', timeout=timeout, check=check))
        if not hasattr(bot, 'wait_for_debug_tasks'):
            bot.wait_for_debug_tasks = dict()
        bot.wait_for_debug_tasks[message.id] = {
            task: task,
            message: message,
            ctx: ctx
        }
        reaction, user = await task
    except asyncio.TimeoutError:
        await message.delete()
        await ctx.send(f"I got no answer within {timeout} seconds.. Aborting.")
    else:
        if reaction.emoji is yes and on_yes is not None:
            if delete:
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
            await on_yes()
        elif reaction.emoji is no:
            if delete:
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass
            if on_no is not None:
                await on_no()
            else:
                await GearbotLogging.send_to(ctx, "NO", "command_canceled")
    del bot.wait_for_debug_tasks[message.id]
