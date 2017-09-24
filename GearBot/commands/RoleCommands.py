from commands.command import Command
import Variables

class RoleCommand(Command):

    def __init__(self, help, role='346629002561060864', extrahelp=None):
        super().__init__(help, extrahelp=extrahelp)
        self.role = role

    def canExecute(self, user):
        if Variables.DEBUG_MODE:
            return True
        for role in user.roles:
            if role.id == self.role:
                return True