import discord
import asyncio
import os

async def send_protected_message(client, channel, text):
    try:
        await client.send_message(channel, '{}'.format(text))
    except discord.Forbidden:
        print("Exception: Bot is not allowed to send messages")
        pass
    except discord.InvalidArgument:
        print("Exception: Invalid message arguments")
        pass
    except Exception as e:
        print("Exception: {}".format(str(e)))
        pass

