# force it to use v6 instead of v7
import asyncio
import os
import signal
import datetime

import aiohttp
import aioredis
import disnake.http
from disnake.ext.commands import ExtensionAlreadyLoaded

from Bot.TheRealGearBot import handle_exception
from database import DatabaseConnector
from views.InfSearch import InfSearch

if 'proxy_url' in os.environ:
    disnake.http.Route.BASE = os.environ['proxy_url']

from argparse import ArgumentParser

from Bot import TheRealGearBot
from Bot.GearBot import GearBot
from Util import Configuration, GearbotLogging, InfractionUtils, Utils, Emoji, Translator
from disnake import Intents, MemberCacheFlags
from kubernetes import client, config

def prefix_callable(bot, message):
    return TheRealGearBot.prefix_callable(bot, message)

async def node_init(generation, resource_version):
    from database import DatabaseConnector
    from database.DatabaseConnector import Node
    await DatabaseConnector.init()
    hostname = os.uname()[1]
    GearbotLogging.info(f"GearBot clusternode {hostname} (generation {generation}). Trying to figure out where i fit in")
    existing = await Node.filter(hostname=hostname, generation=generation).get_or_none()
    if existing is None:
        count = 0
        while count < 100:

            try:
                await Node.create(hostname=hostname, generation=generation, resource_version=resource_version, shard=count)
                return count
            except Exception as ex:
                GearbotLogging.exception("did something go wrong?", ex)
                count += 1
    else:
        return existing.shard


async def initialize(bot):
    await gearbot.login(token)
    try:
        await GearbotLogging.initialize(bot, Configuration.get_master_var("BOT_LOG_CHANNEL"))
        # database
        GearbotLogging.info(f"Cluster {bot.cluster} connecting to the database.")
        await DatabaseConnector.init()
        GearbotLogging.info(f"Cluster {bot.cluster} database connection established.")

        await Emoji.initialize(bot)
        Utils.initialize(bot)
        InfractionUtils.initialize(bot)
        bot.data = {
            "unbans": set(),
            "nickname_changes": set()
        }

        c = await Utils.get_commit()
        bot.version = c
        GearbotLogging.info(f"GearBot cluster {bot.cluster} spinning up version {c}")
        await GearbotLogging.bot_log(
            f"{Emoji.get_chat_emoji('ALTER')} GearBot cluster {bot.cluster} spinning up version {c}")

        socket = Configuration.get_master_var("REDIS_SOCKET", "")
        if socket == "":
            bot.redis_pool = await aioredis.create_redis_pool(
                (Configuration.get_master_var('REDIS_HOST', "localhost"), Configuration.get_master_var('REDIS_PORT', 6379)),
                encoding="utf-8", db=0)
        else:
            bot.redis_pool = await aioredis.create_redis_pool(socket, encoding="utf-8", db=0, maxsize=3)

        GearbotLogging.info("Cluster {bot.cluster} redis connection established")
        await GearbotLogging.bot_log(
            f"{Emoji.get_chat_emoji('YES')} Cluster {bot.cluster} redis connection established, let's go full speed!")

        bot.aiosession = aiohttp.ClientSession()

        await Translator.initialize(bot)
        bot.being_cleaned.clear()
        await Configuration.initialize(bot)

        bot.start_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)

        for extension in Configuration.get_master_var("COGS"):
            try:
                GearbotLogging.info(f"Loading {extension} cog...")
                bot.load_extension("Cogs." + extension)
            except ExtensionAlreadyLoaded:
                pass
            except Exception as e:
                await handle_exception(f"Failed to load cog {extension}", bot, e)
        GearbotLogging.info("Cogs loaded")

        to_unload = Configuration.get_master_var("DISABLED_COMMANDS", [])
        for c in to_unload:
            bot.remove_command(c)

        bot.add_view(InfSearch([], 1, 0))

        bot.STARTUP_COMPLETE = True
        info = await bot.application_info()
        gears = [Emoji.get_chat_emoji(e) for e in ["WOOD", "STONE", "IRON", "GOLD", "DIAMOND"]]
        a = " ".join(gears)
        b = " ".join(reversed(gears))

        await GearbotLogging.bot_log(message=f"{a} {info.name} initialization complete, going online! {b}")
    except Exception as e:
        await handle_exception("Startup failure", bot, e)
        raise e


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--token", help="Specify your Discord token")
    parser.add_argument("--total_shards", help="Total shard count")
    parser.add_argument("--num_shards", help="Amount of shards to start in this cluster")
    parser.add_argument("--offset", help="Shard offset")

    clargs = parser.parse_args()

    GearbotLogging.init_logger(int(clargs.offset) if clargs.offset else 0)

    if 'gearbotlogin' in os.environ:
        token = os.environ['gearbotlogin']
    elif clargs.token:
        token = clargs.token
    elif Configuration.get_master_var("LOGIN_TOKEN", "0") != "0":
        token = Configuration.get_master_var("LOGIN_TOKEN")
    else:
        token = input("Please enter your Discord token: ")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    intents = Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            integrations=False,
            webhooks=False,
            invites=False,
            voice_states=True,
            presences=False,
            messages=True,
            reactions=True,
            typing=False,
            guild_scheduled_events=False,
            message_content=True,
        )
    args = {
        "command_prefix": prefix_callable,
        "case_insensitive": True,
        "max_messages": None,
        "intents": intents,
        "member_cache_flags": MemberCacheFlags.from_intents(intents),
        "chunk_guilds_at_startup": False,
        "monitoring_prefix": Configuration.get_master_var("MONITORING_PREFIX", "gearbot")
    }
    if clargs.total_shards:
        total_shards = int(clargs.total_shards)
        offset = int(clargs.offset)
        num_shards = int(clargs.num_shards)
        args.update({
            "shard_count": total_shards,
            "cluster": offset,
            "shard_ids": [*range(offset * num_shards, (offset * num_shards) + num_shards)]
        })
    elif 'namespace' in os.environ:
        GearbotLogging.info("Determining scaling information from kubernetes ...")
        namespace = os.environ['namespace']
        config.load_incluster_config()
        kubeclient = client.AppsV1Api()
        deployment = kubeclient.read_namespaced_deployment("gearbot", "gearbot")
        print(deployment)
        cluster = loop.run_until_complete(node_init(deployment.status.observed_generation, deployment.metadata.annotations["deployment.kubernetes.io/revision"]))
        num_clusters = deployment.spec.replicas
        args.update({
            "shard_count": num_clusters*2,
            "cluster": cluster,
            "shard_ids": [cluster * 2, (cluster * 2) + 1]
        })

        GearbotLogging.info(f"Ready to go, spinning up as instance {args['cluster'] + 1}/{args['shard_count']}")




    gearbot = GearBot(**args)

    gearbot.remove_command("help")

    # set shutdown hooks
    try:
        for signame in ('SIGINT', 'SIGTERM'):
            asyncio.get_event_loop().add_signal_handler(getattr(signal, signame),
                                                        lambda: asyncio.ensure_future(Utils.cleanExit(gearbot, signame)))
    except Exception as e:
        pass  # doesn't work on windows

    # initialize
    loop.run_until_complete(initialize(gearbot))

    gearbot.run(token)

    GearbotLogging.info("GearBot shutting down, cleaning up")
    gearbot.database_connection.close()
    GearbotLogging.info("Cleanup complete")

GearbotLogging.info("GearBot shutdown completed cleanly")
