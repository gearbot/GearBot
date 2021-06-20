from discord.ext import commands

from Bot.GearBot import GearBot
from Util import Permissioncheckers


class BaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot: GearBot = bot
        name = self.__class__.__name__
        self.permissions = cog_permissions[name] if name in cog_permissions else None

    async def cog_check(self, ctx):
        return Permissioncheckers.check_permission(ctx.command, ctx.guild, ctx.author, self.bot)


# Reference Permissions:
"""
╔════╦═════════════════╦═══════════════════════════════════════════════════╗
║ Nr ║      Name       ║                    Requirement                    ║
╠════╬═════════════════╬═══════════════════════════════════════════════════╣
║  0 ║ Public          ║ Everyone                                          ║
║  1 ║ Trusted         ║ People with a trusted role or mod+                ║
║  2 ║ Mod             ║ People with ban permissions or admin+             ║
║  3 ║ Admin           ║ People with administrator perms or an admin role  ║
║  4 ║ Specific people ║ People you added to the whitelist for a command   ║
║  5 ║ Server owner    ║ The person who owns the server                    ║
║  6 ║ Disabled        ║ Perm level nobody can get, used to disable stuff  ║
╚════╩═════════════════╩═══════════════════════════════════════════════════╝
"""

# All cog permissions lookup table, sorted alphabetically
# The keys are the class name, with identical capitalization
# The above allows for fancy, clean, lookups for what permissions to use
cog_permissions = {
    "AntiRaid": {
        "min": 1,
        "max": 6,
        "required": 2,
        "commands": {
            "enable": {"required": 3, "min": 1, "max": 6, "commands": {}},
            "disable": {"required": 3, "min": 1, "max": 6, "commands": {}},
        }
    },

    "Basic": {
        "min": 0,
        "max": 6,
        "required": 0,
        "commands": {}
    },

    "BCVersionChecker": {
        "min": 0,
        "max": 6,
        "required": 0,
        "commands": {}
    },

    "CustCommands": {
        "min": 0,
        "max": 6,
        "required": 0,
        "commands": {
            "commands": {
                "required": 0,
                "min": 0,
                "max": 6,
                "commands": {
                    "create": {"required": 2, "min": 1, "max": 6, "commands": {}},
                    "remove": {"required": 2, "min": 1, "max": 6, "commands": {}},
                    "update": {"required": 2, "min": 1, "max": 6, "commands": {}},
                }
            }
        }
    },

    "Emoji": {
        "min": 1,
        "max": 6,
        "required": 3,
        "commands": {
            "emoji": {
                "min": 1,
                "max": 6,
                "required": 3,
                "commands": {
                    "list": {
                        "min": 0,
                        "max": 6,
                        "required": 3
                    }
                }
            }
        }
    },

    "Fun": {
        "min": 0,
        "max": 6,
        "required": 0,
        "commands": {}
    },

    "Infractions": {
        "min": 1,
        "max": 6,
        "required": 2,
        "commands": {
            "inf": {
                "required": 2,
                "min": 1,
                "max": 6,
                "commands": {
                    "delete": {"required": 5, "min": 1, "max": 6}
                }
            }
        }
    },

    "Minecraft": {
        "min": 0,
        "max": 6,
        "required": 0,
        "commands": {}
    },

    "Moderation": {
        "min": 1,
        "max": 6,
        "required": 2,
        "commands": {
            "userinfo": {"required": 2, "min": 0, "max": 6},
            "serverinfo": {"required": 2, "min": 0, "max": 6},
            "roles": {"required": 2, "min": 0, "max": 6},
            "verification": {"required": 3, "min": 2, "max": 6},
        }
    },

    "Reminders": {
        "min": 0,
        "max": 6,
        "required": 0,
        "commands": {}
    },

    "ServerAdmin": {
        "min": 2,
        "max": 5,
        "required": 3,
        "commands": {
            "configure": {
                "min": 2,
                "max": 5,
                "required": 3,
                "commands": {
                    "lvl4": {"required": 5, "min": 4, "max": 6}
                }
            }
        }
    }
}
