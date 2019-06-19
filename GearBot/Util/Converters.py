from discord import NotFound, Forbidden, HTTPException
from discord.ext.commands import UserConverter, BadArgument, Converter

from Bot.TheRealGearBot import PostParseError
from Util import Utils, Configuration, Translator
from Util.Matchers import *
from database import DBUtils
from database.DatabaseConnector import LoggedMessage, Infraction


class TranslatedBadArgument(BadArgument):
    def __init__(self, key, ctx, arg=None, **kwargs):
        super().__init__(Translator.translate(key, ctx, arg=Utils.trim_message(Utils.clean_name(str(arg)), 1000), **kwargs))


class BannedMember(Converter):
    async def convert(self, ctx, argument):
        try:
            entity = await ctx.guild.fetch_ban(await DiscordUser().convert(ctx, argument))
        except NotFound:
            raise TranslatedBadArgument("not_banned", ctx)
        return entity


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
                user = await Utils.get_user(
                    await RangedInt(min=20000000000000000, max=9223372036854775807).convert(ctx, argument))
            except (ValueError, HTTPException):
                pass

        if user is None or (self.id_only and str(user.id) != argument):
            raise TranslatedBadArgument('user_conversion_failed', ctx, arg=argument)
        return user


class ApexPlatform(Converter):
    async def convert(self, ctx, argument):
        argument = argument.lower()
        if argument == "pc":
            platformid = "5"
        elif argument == "psn":
            platformid = "2"
        elif argument == "xbox":
            platformid = "1"
        else:
            raise TranslatedBadArgument("apexstats_invalid_platform", ctx)
        return platformid

class UserID(Converter):
    async def convert(self, ctx, argument):
        return (await DiscordUser().convert(ctx, argument)).id

class Reason(Converter):
    async def convert(self, ctx, argument):
        argument = argument.strip("|").strip().replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
        for match in EMOJI_MATCHER.finditer(argument):
            argument = argument.replace(match.group(0), f":{match.group(2)}:")
        if len(argument) > 1800:
            raise TranslatedBadArgument('reason_too_long', ctx)
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


class Message(Converter):

    def __init__(self, insert=False, local_only=False) -> None:
        self.insert = insert
        self.local_only = local_only

    async def convert(self, ctx, argument):
        async with ctx.typing():
            message_id, channel_id = self.extract_ids(ctx, argument)
            logged, message, = await self.fetch_messages(ctx, message_id, channel_id)
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
    async def fetch_messages(ctx, message_id, channel_id):
        message = None
        logged_message = LoggedMessage.get_or_none(messageid=message_id)
        async with ctx.typing():
            if logged_message is None:
                if channel_id is None:
                    for channel in ctx.guild.text_channels:
                        try:
                            permissions = channel.permissions_for(channel.guild.me)
                            if permissions.read_messages and permissions.read_message_history:
                                message = await channel.fetch_message(message_id)
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
                        message = await channel.fetch_message(message_id)
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
        argument = argument.strip('#')
        try:
            argument = int(argument)
        except ValueError:
            raise TranslatedBadArgument('NaN', ctx)
        infraction = Infraction.get_or_none(id=argument, guild_id=ctx.guild.id)
        if infraction is None:
            raise TranslatedBadArgument('inf_not_found', ctx, id=argument)
        else:
            return infraction

class DurationHolder:

    def __init__(self, length, unit=None) -> None:
        super().__init__()
        self.length = length
        self.unit = unit

    def to_seconds(self, ctx):
        if self.unit is None:
            self.unit = "seconds"
        unit = self.unit.lower()
        length = self.length
        if len(unit) > 1 and unit[-1:] == 's':  # plural -> singular
            unit = unit[:-1]
        if unit == 'w' or unit == 'week':
            length = length * 7
            unit = 'd'
        if unit == 'd' or unit == 'day':
            length = length * 24
            unit = 'h'
        if unit == 'h' or unit == 'hour':
            length = length * 60
            unit = 'm'
        if unit == 'm' or unit == 'minute':
            length = length * 60
            unit = 's'
        if unit != 's' and unit != 'second':
            raise PostParseError('Duration', 'Not a valid duration identifier')
        if length > 60 * 60 * 24 * 365:
            raise PostParseError('Duration', Translator.translate('max_duration', ctx))
        else:
            return length

    def __str__(self):
        if len(self.unit) == 1:
            return f"{self.length}{self.unit}"
        if self.unit[-1] != "s":
            return f"{self.length} {self.unit}s"
        return f"{self.length} {self.unit}"


class Duration(Converter):
    async def convert(self, ctx, argument):
        match = START_WITH_NUMBER_MATCHER.match(argument)
        if match is None:
            raise TranslatedBadArgument('NaN', ctx)
        group = match.group(1)
        holder = DurationHolder(int(group))
        if len(argument) > len(group):
            holder.unit = await DurationIdentifier().convert(ctx, argument[len(group):])
        return holder


class DurationIdentifier(Converter):
    async def convert(self, ctx, argument):
        if argument is None:
            argument = "seconds"
        if argument.lower() not in ["week", "weeks", "day", "days", "hour", "hours", "minute", "minutes", "second",
                                    "seconds", "w", "d", "h", "m", "s"]:
            raise BadArgument("Invalid duration, valid identifiers: week(s), day(s), hour(s), minute(s), second(s)")
        return argument

class EmojiName(Converter):
    async def convert(self, ctx, argument):
        if len(argument) < 2 or len(argument) > 32:
            raise TranslatedBadArgument('emoji_name_too_short', ctx, argument)
        if len(argument) > 32:
            raise TranslatedBadArgument('emoji_name_too_long', ctx, argument)
        if " " in argument:
            raise TranslatedBadArgument('emoji_name_space', ctx, argument)
        return argument
