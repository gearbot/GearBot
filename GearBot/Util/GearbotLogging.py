import traceback

import discord
import logging
import datetime
import time

import Variables


async def logToLogChannel(text):
    try:
        await Variables.DISCORD_CLIENT.send_message(Variables.BOT_LOG_CHANNEL, '{}'.format(text))
    except discord.Forbidden:
        logging.error("Exception: Bot is not allowed to send messages in logging channel")
        pass
    except discord.InvalidArgument:
        logging.warning("Exception: Invalid message arguments")
        pass
    except Exception as e:
        logging.error("Exception: {}".format(str(e)))
        pass

async def logToModChannel(text):
    try:
        await Variables.DISCORD_CLIENT.send_message(Variables.MOD_LOG_CHANNEL, '{}'.format(text))
    except discord.Forbidden:
        logging.error("Exception: Bot is not allowed to send messages in logging channel")
        pass
    except discord.InvalidArgument:
        logging.warning("Exception: Invalid message arguments")
        pass
    except Exception as e:
        logging.error("Exception: {}".format(str(e)))
        pass


async def on_command_error(channel, cmd, args, exception):
    try:
        logging.warning("Command execution failed:"
                        f"    Command: {cmd}"
                        f"    Arguments: {args}"
                        f"    Channel: {channel.name}"
                        f"    Exception: {exception}")
        await Variables.DISCORD_CLIENT.send_message(channel, f"Execution of the {cmd} command failed, please try again later")
    except Exception as e:
        logging.warning(f"Failed to notify caller:\n{e}")

    try:
        embed = discord.Embed(colour=discord.Colour(0xff0000),
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))

        embed.set_author(name="Command execution failed")

        embed.add_field(name="Command", value=cmd)
        embed.add_field(name="Arguments", value=args)
        embed.add_field(name="Channel", value=channel.name)
        embed.add_field(name="Exception", value=exception)
        embed.add_field(name="Stacktrace", value=traceback.format_exc())

        await Variables.DISCORD_CLIENT.send_message(Variables.BOT_LOG_CHANNEL, embed=embed)
    except Exception as e:
        logging.error(f"Failed to log to logging channel:\n{e}")