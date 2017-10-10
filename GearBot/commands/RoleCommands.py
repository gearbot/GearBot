from commands.command import Command
import Variables


class RoleCommand(Command):
    def __init__(self, role='346629002561060864'):
        super().__init__()
        self.role = role

    def canExecute(self, user):
        if Variables.DEBUG_MODE:
            return True
        if user.roles is None:
            return False
        for role in user.roles:
            if role.id == self.role:
                return True
        return False
