from discord import AutoShardedClient


class GearBot(AutoShardedClient):
    STARTUP_COMPLETE = False
    user_messages = 0
    bot_messages = 0
    self_messages = 0
    commandCount = 0
    custom_command_count = 0
    errors = 0
    eaten = 0
    database_errors = 0
    hot_reloading = False

    def __init__(self, *args, loop=None, **kwargs):
        super().__init__(*args, loop=loop, **kwargs)

