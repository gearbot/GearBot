import importlib

from Bot import Reloader, TheRealGearBot
from Util import GearbotLogging, Emoji, Utils, Translator, Configuration


async def upgrade(name, bot):
    await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('REFRESH')} Upgrade initiated by {name}")
    GearbotLogging.info(f"Upgrade initiated by {name}")
    file = open("upgradeRequest", "w")
    file.write("upgrade requested")
    file.close()
    await bot.logout()


async def update(name, bot):
    message = await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('REFRESH')} Hot reload in progress... (initiated by {name})")
    await Utils.execute(["git pull origin master"])
    GearbotLogging.info("Initiating hot reload")
    antiraid = bot.get_cog('AntiRaid')
    trackers = None
    if antiraid is not None:
        trackers = antiraid.raid_trackers
    untranslatable = Translator.untranlatable
    importlib.reload(Reloader)
    for c in Reloader.components:
        importlib.reload(c)
    Translator.untranlatable = untranslatable
    GearbotLogging.info("Reloading all cogs...")
    temp = []
    for cog in bot.cogs:
        temp.append(cog)
    for cog in temp:
        bot.unload_extension(f"Cogs.{cog}")
        GearbotLogging.info(f'{cog} has been unloaded.')
        bot.load_extension(f"Cogs.{cog}")
        GearbotLogging.info(f'{cog} has been loaded.')
    to_unload = Configuration.get_master_var("DISABLED_COMMANDS", [])
    for c in to_unload:
        bot.remove_command(c)

    antiraid = bot.get_cog('AntiRaid')
    if antiraid is not None and trackers is not None:
        antiraid.raid_trackers = trackers

    await TheRealGearBot.initialize(bot)
    c = await Utils.get_commit()
    GearbotLogging.info(f"Hot reload complete, now running on {c}")
    bot.version = c
    bot.hot_reloading = False
    m = f"{Emoji.get_chat_emoji('YES')} Hot reload complete, now running on {bot.version} (update initiated by {name})"
    await message.edit(content=m)
    bot.loop.create_task(Translator.upload())