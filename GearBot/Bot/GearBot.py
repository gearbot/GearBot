import asyncio
import time
from asyncio import Queue
from collections import deque

from disnake.ext.commands import AutoShardedBot
from prometheus_client import CollectorRegistry

from Bot import TheRealGearBot
from Util.PromMonitors import PromMonitors


class GearBot(AutoShardedBot):
    STARTUP_COMPLETE = False
    user_messages = 0
    bot_messages = 0
    self_messages = 0
    commandCount = 0
    custom_command_count = 0
    errors = 0
    eaten = 0
    database_errors = 0,
    database_connection = None
    locked = True
    redis_pool = None
    aiosession = None
    being_cleaned = dict()
    metrics_reg = CollectorRegistry()
    version = ""
    dash_guild_users = set()
    dash_guild_watchers = dict()
    cluster = 0
    shard_count = 1
    shard_ids = [],
    chunker_active = False
    chunker_pending = False
    chunker_should_terminate = False
    chunker_queue = Queue()
    deleted_messages = deque(maxlen=500)

    def __init__(self, *args, loop=None, **kwargs):
        super().__init__(*args, loop=loop, **kwargs)
        self.metrics = PromMonitors(self, kwargs.get("monitoring_prefix", "gearbot"))
        self.cluster = kwargs.get("cluster", 0)
        self.total_shards = kwargs.get("shard_count", 1)
        self.shard_ids = kwargs.get("shard_ids", [0])

    def dispatch(self, event_name, *args, **kwargs):
        if "socket" not in event_name not in ["message_edit"]:
            self.metrics.bot_event_counts.labels(event_name=event_name, cluster=self.cluster).inc()
        super().dispatch(event_name, *args, **kwargs)

    #### event handlers, basically bouncing everything to TheRealGearBot file so we can hotreload our listeners

    async def on_connect(self):
        await TheRealGearBot.on_connect(self)

    async def on_ready(self):
        await TheRealGearBot.on_ready(self)

    async def on_message(self, message):
        await TheRealGearBot.on_message(self, message)

    async def on_guild_join(self, guild):
        await TheRealGearBot.on_guild_join(self, guild)

    async def on_guild_remove(self, guild):
        await TheRealGearBot.on_guild_remove(self, guild)

    async def on_command_error(self, ctx, error):
        await TheRealGearBot.on_command_error(self, ctx, error)

    async def on_error(self, event, *args, **kwargs):
        await TheRealGearBot.on_error(self, event, *args, **kwargs)

    async def on_guild_update(self, before, after):
        await TheRealGearBot.on_guild_update(before, after)

    async def on_thread_create(self, thread):
        await TheRealGearBot.on_thread_create(self, thread)

    #### reloading
