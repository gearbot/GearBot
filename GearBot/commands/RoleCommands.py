from .command import Command


class RoleCommand(Command):

    def __init__(self, help, role):
        super().__init__(help)
        self.role = role #internal role/group

    def canExecute(self, user):
        return True #TODO: aquire required role for this command from config
