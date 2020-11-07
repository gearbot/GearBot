from discord import Member

from Util import Translator, MessageUtils, Utils, Emoji


class ActionFailed(Exception):

    def __init__(self, message) -> None:
        super().__init__()
        self.message = message


async def act(ctx, name, target, handler, allow_bots=True, require_on_server=True, send_message=True, check_bot_ability=True, **kwargs):
    user = await Utils.get_member(ctx.bot, ctx.guild, target)
    if user is None:
        if require_on_server:
            message = Translator.translate('user_not_on_server', ctx.guild.id)
            if send_message:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {message}")
            return False, message
        else:
            user = ctx.bot.get_user(target)
    if user is None and not require_on_server:
        user = await Utils.get_user(target)
    if user is None:
        return False, "Unknown user"
    allowed, message = can_act(name, ctx, user, require_on_server=require_on_server, action_bot=allow_bots, check_bot_ability=check_bot_ability)
    if allowed:
        try:
            await handler(ctx, user, **kwargs)
            return True, None
        except ActionFailed as ex:
            return False, ex.message

    else:
        if send_message:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {message}")
        return False, message


async def mass_action(ctx, name, targets, handler, allow_duplicates=False, allow_bots=True, max_targets=None, require_on_server=True, **kwargs):
    if max_targets is not None and len(targets) > max_targets:
        await MessageUtils.send_to(ctx, "NO", "mass_action_too_many_people", max=max_targets)
        return
    failed = []
    handled = set()
    if kwargs["dm_action"] and len(targets) > 5:
        await MessageUtils.send_to(ctx, "NO", "mass_action_too_many_people_dm", max=5)
        kwargs["dm_action"]=False
    for target in targets:
        if not allow_duplicates and target in handled:
            failed.append(f"{target}: {Translator.translate('mass_action_duplicate', ctx)}")
        else:
            done, error = await act(ctx, name, target, handler, allow_bots, require_on_server=require_on_server, send_message=False, **kwargs)
            if not done:
                failed.append(f"{target}: {error}")
            else:
                handled.add(target)

    return failed


def can_act(action, ctx, user, require_on_server=True, action_bot=True, check_bot_ability=True):
    is_member = isinstance(user, Member)
    if not require_on_server and not is_member:
        return True, None
    if (not is_member) and require_on_server:
        return False, Translator.translate("user_not_on_server", ctx.guild.id)

    if check_bot_ability and user.top_role >= ctx.guild.me.top_role:
        return False, Translator.translate(f'{action}_unable', ctx.guild.id, user=Utils.clean_user(user))

    if ((ctx.author != user and ctx.author.top_role > user.top_role) or (
            ctx.guild.owner == ctx.author)) and user != ctx.guild.owner and user != ctx.bot.user and ctx.author != user:
        return True, None
    if user.bot and not action_bot:
        return False, Translator.translate(f"cant_{action}_bot", ctx.guild.id, user=user)

    return False, Translator.translate(f'{action}_not_allowed', ctx.guild.id, user=user)
