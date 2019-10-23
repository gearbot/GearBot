import os
from argparse import ArgumentParser

from Bot import TheRealGearBot
from Bot.GearBot import GearBot


def prefix_callable(bot, message):
    return TheRealGearBot.prefix_callable(bot, message)


gearbot: GearBot = None

from Util import Configuration, GearbotLogging

if __name__ == '__main__':
    gearbot = GearBot(command_prefix=prefix_callable, case_insensitive=True,
              max_messages=100)  # 100 is the min for some reason
    parser = ArgumentParser()
    parser.add_argument("--token", help="Specify your Discord token")

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
    gearbot.remove_command("help")
    GearbotLogging.info("Ready to go, spinning up the gears")
    gearbot.run(token)
    GearbotLogging.info("GearBot shutting down, cleaning up")
    gearbot.database_connection.close()
    GearbotLogging.info("Cleanup complete")
