# force it to use v6 instead of v7
import discord.http

discord.http.Route.BASE = 'https://discordapp.com/api/v6'

import os
from argparse import ArgumentParser

from Bot import TheRealGearBot
from Bot.GearBot import GearBot
from Util import Configuration, GearbotLogging


def prefix_callable(bot, message):
    return TheRealGearBot.prefix_callable(bot, message)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--token", help="Specify your Discord token")
    parser.add_argument("--total_shards", help="Total shard count")
    parser.add_argument("--num_shards", help="Amount of shards to start in this cluster")
    parser.add_argument("--offset", help="Shard offset")

    GearbotLogging.init_logger()

    clargs = parser.parse_args()
    if 'gearbotlogin' in os.environ:
        token = os.environ['gearbotlogin']
    elif clargs.token:
        token = clargs.token
    elif not Configuration.get_master_var("LOGIN_TOKEN", "0") is "0":
        token = Configuration.get_master_var("LOGIN_TOKEN")
    else:
        token = input("Please enter your Discord token: ")

    args = {
        "command_prefix": prefix_callable,
        "case_insensitive": True,
        "max_messages": None,
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

    gearbot = GearBot(**args)

    gearbot.remove_command("help")
    GearbotLogging.info("Ready to go, spinning up the gears")
    gearbot.run(token)
    GearbotLogging.info("GearBot shutting down, cleaning up")
    gearbot.database_connection.close()
    GearbotLogging.info("Cleanup complete")
