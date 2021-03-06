# force it to use v6 instead of v7
import asyncio

import discord.http

# discord.http.Route.BASE = 'http://http-proxy/api/v6'

import os
from argparse import ArgumentParser

from Bot import TheRealGearBot
from Bot.GearBot import GearBot
from Util import Configuration, GearbotLogging
from discord import Intents, MemberCacheFlags
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
    elif not Configuration.get_master_var("LOGIN_TOKEN", "0") is "0":
        token = Configuration.get_master_var("LOGIN_TOKEN")
    else:
        token = input("Please enter your Discord token: ")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    args = {
        "command_prefix": prefix_callable,
        "case_insensitive": True,
        "max_messages": None,
        "intents": Intents(
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
        ),
        "member_cache_flags": MemberCacheFlags(
            online=False,
            voice=True,
            joined=True,
        ),
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
            "shard_count": num_clusters,
            "cluster": cluster,
            "shard_ids": [cluster]
        })

        GearbotLogging.info(f"Ready to go, spinning up as instance {args['cluster'] + 1}/{args['shard_count']}")




    gearbot = GearBot(**args)

    gearbot.remove_command("help")
    gearbot.run(token)
    GearbotLogging.info("GearBot shutting down, cleaning up")
    gearbot.database_connection.close()
    GearbotLogging.info("Cleanup complete")

