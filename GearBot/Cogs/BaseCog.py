from discord.ext import commands

from Bot.GearBot import GearBot
from Util import Permissioncheckers


class BaseCog(commands.Cog):
    def __init__(self, bot, permissions=None):
        self.bot:GearBot = bot
        self.permissions=permissions

    async def cog_check (self, ctx):
        return Permissioncheckers.check_permission(ctx)