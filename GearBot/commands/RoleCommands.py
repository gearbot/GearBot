from commands.command import Command
from commands.util import DEBUG_MODE


class RoleCommand(Command):

    def __init__(self, help, role):
        super().__init__(help)
        self.role = role #internal role/group

    def canExecute(self, user):
        return DEBUG_MODE or "350928446794235904" in user.roles
