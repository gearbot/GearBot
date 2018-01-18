import datetime
import logging
import time
import traceback

import discord

import Variables


async def logToLogChannel(text = None, embed = None):
    try:
        await Variables.DISCORD_CLIENT.send_message(Variables.BOT_LOG_CHANNEL, text, embed=embed)
    except discord.Forbidden:
        logging.error("Exception: Bot is not allowed to send messages in logging channel")
    except discord.InvalidArgument:
        logging.error("Exception: Invalid message arguments")
    except Exception as e:
        logging.error("Exception: {}".format(str(e)))


async def logToModChannel(text = None, embed=None):
    try:
        await Variables.DISCORD_CLIENT.send_message(Variables.MOD_LOG_CHANNEL, text='{}'.format(text), embed=embed)
    except discord.Forbidden:
        logging.error("Exception: Bot is not allowed to send messages in logging channel")
    except discord.InvalidArgument:
        logging.error("Exception: Invalid message arguments")
    except Exception as e:
        logging.error("Exception: {}".format(str(e)))


async def on_command_error(channel:discord.Channel, sender:discord.User, cmd, args, exception):
    try:
        logging.error("Command execution failed:"
                        f"    Command: {cmd}"
                        f"    Arguments: {args}"
                        f"    Channel: {'Private Message' if channel.is_private else channel.name}"
                        f"    Sender: {sender.name}#{sender.discriminator}"
                        f"    Exception: {exception}")
        await Variables.DISCORD_CLIENT.send_message(channel,
            f"Execution of the {cmd} command failed, please try again later")
    except Exception as e:
        logging.error(f"Failed to notify caller:\n{e}")

    try:
        embed = discord.Embed(colour=discord.Colour(0xff0000),
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))

        embed.set_author(name="Command execution failed")

        embed.add_field(name="Command", value=cmd)
        embed.add_field(name="Arguments", value=args)
        embed.add_field(name="Channel", value='Private Message' if channel.is_private else channel.name)
        embed.add_field(name="Sender", value=f"{sender.name}#{sender.discriminator}")
        embed.add_field(name="Exception", value=exception)
        embed.add_field(name="Stacktrace", value=traceback.format_exc())

        await Variables.DISCORD_CLIENT.send_message(Variables.BOT_LOG_CHANNEL, embed=embed)
    except Exception as e:
        logging.error(f"Failed to log to logging channel:\n{e}")