from Cogs.BaseCog import BaseCog
from Util import Configuration


class Fun(BaseCog):

    def __init__(self, bot):
        super().__init__(bot, {
            "min": 0,
            "max": 6,
            "required": 0,
            "commands": {}
        })
        to_remove = {
            "CAT_KEY": "cat",
            "DOG_KEY": "dog",
            "APEX_KEY": "apexstats"
        }
        for k, v in to_remove.items():
            if Configuration.get_master_var(k, "0") is "0":
                bot.remove_command(v)
