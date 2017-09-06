from commands.command import Command
from commands.util import DEBUG_MODE


class RoleCommand(Command):

    def __init__(self, help, role):
        super().__init__(help)
        self.role = role #internal role/group

    def canExecute(self, user):
        global DEBUG_MODE
        if DEBUG_MODE:
            return True
        for role in user.roles:
            if role.id == '346629002561060864':
                return True