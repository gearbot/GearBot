import re

from discord import NotFound, Forbidden, HTTPException
from discord.ext.commands import UserConverter, BadArgument, Converter

from Util import Utils, Configuration, Translator
from database import DBUtils
from database.DatabaseConnector import LoggedMessage, Infraction


class TranslatedBadArgument(BadArgument):
    def __init__(self, key, ctx, arg=None, **kwargs):
        super().__init__(Translator.translate(key, ctx, arg=Utils.clean_name(str(arg)), **kwargs))


class BannedMember(Converter):
    async def convert(self, ctx, argument):
        try:
            entity = await ctx.guild.get_ban(await DiscordUser().convert(ctx, argument))
        except NotFound:
            raise TranslatedBadArgument("not_banned", ctx)
        return entity


ID_MATCHER = re.compile("<@!?([0-9]+)>")


class DiscordUser(Converter):


    def __init__(self, id_only=False) -> None:
        super().__init__()
        self.id_only = id_only

    async def convert(self, ctx, argument):
        user = None
        match = ID_MATCHER.match(argument)
        if match is not None:
            argument = match.group(1)
        try:
            user = await UserConverter().convert(ctx, argument)
        except BadArgument:
            try:
                user = await Utils.get_user(await RangedInt(min=20000000000000000, max=9223372036854775807).convert(ctx, argument))
            except (ValueError, HTTPException):
                pass

        if user is None or (self.id_only and str(user.id) != argument):
            raise TranslatedBadArgument('user_conversion_failed', ctx, arg=argument)
        return user


class UserID(Converter):
    async def convert(self, ctx, argument):
        return (await DiscordUser().convert(ctx, argument)).id


EMOJI_MATCHER = re.compile('<a*:([^:]+):(?:[0-9]+)>')


class Reason(Converter):
    async def convert(self, ctx, argument):
        for match in EMOJI_MATCHER.finditer(argument):
            argument = argument.replace(match.group(0), f":{match.group(1)}:")
        if len(argument) > 1800:
            raise TranslatedBadArgument('reason_too_long', ctx)
        return argument


class Duration(Converter):
    async def convert(self, ctx, argument):
        if argument.lower() not in ["week", "weeks", "day", "days", "hour", "hours", "minute", "minutes", "second",
                                    "seconds", "w", "d", "h", "m", "s"]:
            raise BadArgument("Invalid duration, valid identifiers: week(s), day(s), hour(s), minute(s), second(s)")
        return argument


class PotentialID(Converter):
    async def convert(self, ctx, argument):
        match = ID_MATCHER.match(argument)
        if match is not None:
            argument = match.group(1)
        try:
            argument = int(argument)
        except ValueError:
            raise TranslatedBadArgument("no_potential_id", ctx, arg=argument)
        else:
            return argument


CHANNEL_ID_MATCHER = re.compile("<#([0-9]+)>")


class LoggingChannel(Converter):
    async def convert(self, ctx, argument):
        channels = Configuration.get_var(ctx.guild.id, "LOG_CHANNELS")
        match = CHANNEL_ID_MATCHER.match(argument)
        if match is not None:
            argument = match.group(1)
        if argument not in channels:
            raise TranslatedBadArgument('no_log_channel', ctx, arg=argument)
        return argument


class RoleMode(Converter):
    async def convert(self, ctx, argument):
        argument = argument.lower()
        options = [
            "alphabetic",
            "hierarchy",
        ]
        if argument in options:
            return argument
        raise BadArgument(f"Unknown mode, valid modes: {', '.join(options)}")


class Guild(Converter):

    async def convert(self, ctx, argument):
        try:
            argument = int(argument)
        except ValueError:
            raise BadArgument(f"Not a server ID")
        else:
            guild = ctx.bot.get_guild(argument)
            if guild is None:
                raise TranslatedBadArgument("unknown_server", ctx, arg=argument)
            else:
                return guild


JUMP_LINK_MATCHER = re.compile(r"https://(?:canary|ptb)?\.?discordapp.com/channels/\d*/(\d*)/(\d*)")


class Message(Converter):

    def __init__(self, insert=False, local_only=False) -> None:
        self.insert = insert
        self.local_only = local_only

    async def convert(self, ctx, argument):
        async with ctx.typing():
            message_id, channel_id = self.extract_ids(ctx, argument)
            logged, message, = await self.get_messages(ctx, message_id, channel_id)
            if message is None:
                raise TranslatedBadArgument('unknown_message', ctx)
            if logged is None and message is not None and self.insert:
                logged = DBUtils.insert_message(message)
            if logged is not None and logged.content != message.content:
                logged.content = message.content
                logged.save()
        if message.channel != ctx.channel and self.local_only:
            raise TranslatedBadArgument('message_wrong_channel', ctx)
        return message

    @staticmethod
    def extract_ids(ctx, argument):
        message_id = None
        channel_id = None
        if "-" in argument:
            parts = argument.split("-")
            if len(parts) is 2:
                try:
                    channel_id = int(parts[0].strip(" "))
                    message_id = int(parts[1].strip(" "))
                except ValueError:
                    pass
            else:
                parts = argument.split(" ")
                if len(parts) is 2:
                    try:
                        channel_id = int(parts[0].strip(" "))
                        message_id = int(parts[1].strip(" "))
                    except ValueError:
                        pass
        else:
            result = JUMP_LINK_MATCHER.match(argument)
            if result is not None:
                channel_id = int(result.group(1))
                message_id = int(result.group(2))
            else:
                try:
                    message_id = int(argument)
                except ValueError:
                    pass
        if message_id is None:
            raise TranslatedBadArgument('message_invalid_format', ctx)
        return message_id, channel_id

    @staticmethod
    async def get_messages(ctx, message_id, channel_id):
        message = None
        logged_message = LoggedMessage.get_or_none(messageid=message_id)
        async with ctx.typing():
            if logged_message is None:
                if channel_id is None:
                    for channel in ctx.guild.text_channels:
                        try:
                            permissions = channel.permissions_for(channel.guild.me)
                            if permissions.read_messages and permissions.read_message_history:
                                message = await channel.get_message(message_id)
                                channel_id = channel.id
                                break
                        except (NotFound, Forbidden):
                            pass
                    if message is None:
                        raise TranslatedBadArgument('message_missing_channel', ctx)
            elif channel_id is None:
                channel_id = logged_message.channel
            channel = ctx.bot.get_channel(channel_id)
            if channel is None:
                raise TranslatedBadArgument('unknown_channel', ctx)
            elif message is None:
                try:
                    permissions = channel.permissions_for(channel.guild.me)
                    if permissions.read_messages and permissions.read_message_history:
                        message = await channel.get_message(message_id)
                except (NotFound, Forbidden):
                    raise TranslatedBadArgument('unknown_message', ctx)

        return logged_message, message


class RangedInt(Converter):

    def __init__(self, min=None, max=None) -> None:
        self.min = min
        self.max = max

    async def convert(self, ctx, argument) -> int:
        try:
            argument = int(argument)
        except ValueError:
            raise TranslatedBadArgument('NaN', ctx)
        else:
            if self.min is not None and argument < self.min:
                raise TranslatedBadArgument('number_too_small', ctx, min=self.min)
            elif self.max is not None and argument > self.max:
                raise TranslatedBadArgument('number_too_big', ctx, max=self.max)
            else:
                return argument


class RangedIntBan(RangedInt):

    def __init__(self, ) -> None:
        super().__init__(1, 7)


class ListMode(Converter):
    async def convert(self, ctx, argument):
        argument = argument.lower()
        if argument == "whitelist":
            return True
        elif argument == "blacklist":
            return False
        else:
            raise TranslatedBadArgument("invalid_mode", ctx)


class ReminderText(Converter):
    async def convert(self, ctx, argument):
        if len(argument) > 1800:
            raise TranslatedBadArgument('reminder_too_long', ctx)
        return argument


class InfSearchLocation(Converter):
    async def convert(self, ctx, argument):
        values = ["[mod]", "[reason]", "[user]"]
        if argument.lower() in values:
            return argument.lower()
        raise BadArgument("Does this even show up?")


MODIFIER_MATCHER = re.compile(r"^\[(.*):(.*)\]$")


class CommandModifier(Converter):
    def __init__(self, allowed_values, should_lower=True) -> None:
        self.allowed_values = allowed_values
        self.should_lower = should_lower
        super().__init__()

    async def convert(self, ctx, argument):
        if self.should_lower:
            argument = argument.lower()
        match = MODIFIER_MATCHER.match(argument)
        if match is None:
            raise BadArgument("Not a modifier")
        key = match.group(1)
        value = match.group(2)
        if key not in self.allowed_values:
            raise BadArgument("Invalid key")
        for v in self.allowed_values[key]:
            if isinstance(v, Converter):
                return key, v.convert(ctx, value)
            elif v == value:
                return key, value
        raise BadArgument("Not an acceptable value")


class InfSearchModifiers(CommandModifier):
    def __init__(self) -> None:
        super().__init__(allowed_values=dict(search=["mod", "reason", "user"]))


class ServerInfraction(Converter):

    async def convert(self, ctx, argument):
        infraction = Infraction.get_or_none(id=argument, guild_id=ctx.guild.id)
        if infraction is None:
            raise TranslatedBadArgument('inf_not_found', ctx, id=argument)
        else:
            return infraction