import discord

DEBUG_MODE = False
APP_INFO = None
DISCORD_CLIENT: discord.Client = None
HAS_STARTED = False

#Config vars for easy using
BOT_LOG_CHANNEL:discord.Channel = None
MOD_LOG_CHANNEL:discord.Channel = None
ANNOUNCEMENTS_CHANNEL:discord.Channel = None
TESTING_CHANNEL:discord.Channel = None
PREFIX = None
CUSTOM_COMMANDS = dict()

GENERAL_CHANNEL:discord.Channel = None