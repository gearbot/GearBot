import discord

import Variables
from commands.command import Command


class RoleCommand(Command):
    def __init__(self, role='346629002561060864'):
        super().__init__()
        self.role = role

    def canExecute(self, user:discord.User):
        if user.roles is None:
            return False
        for role in user.roles:
            if role.id == self.role:
                return True
        if Variables.DEBUG_MODE or user.id == Variables.APP_INFO.owner.id:
            return True
        return False
