import asyncio

from discord.ext.commands import AutoShardedBot

from Bot import TheRealGearBot


class GearBot(AutoShardedBot):
    STARTUP_COMPLETE = False
    user_messages = 0
    bot_messages = 0
    self_messages = 0
    commandCount = 0
    custom_command_count = 0
    errors = 0
    eaten = 0
    database_errors = 0
    locked = False

    def __init__(self, *args, loop=None, **kwargs):
        super().__init__(*args, loop=loop, **kwargs)

    async def handle_event(self, handler):
        while self.locked:
            await asyncio.sleep(1)
        try:
            await handler
        except Exception as ex:
            pass
        finally:
           pass


    async def _run_event(self, coro, event_name, *args, **kwargs):
        return await super()._run_event(coro, event_name, *args, **kwargs)


    #### event handlers

    async def on_ready(self):
        await TheRealGearBot.on_ready(self)

    async def on_message(self, message):
        await TheRealGearBot.on_message(self, message)

    async def on_guild_join(self, guild):
        await TheRealGearBot.on_guild_join(guild)

    async def on_guild_remove(self, guild):
        await TheRealGearBot.on_guild_remove(guild)

    async def on_command_error(self, ctx, error):
        await TheRealGearBot.on_command_error(self, ctx, error)

    async def on_error(self, event, *args, **kwargs):
        await TheRealGearBot.on_error(self, event, *args, **kwargs)



    #### reloading

