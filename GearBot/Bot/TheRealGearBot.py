import GearBot
from Util import Configuration, GearbotLogging


def prefix_callable(bot, message):
    user_id = bot.user.id
    prefixes = [f'<@!{user_id}> ', f'<@{user_id}> '] #execute commands by mentioning
    if message.guild is None:
        prefixes.append('!') #use default ! prefix in DMs
    elif bot.STARTUP_COMPLETE:
        prefixes.append(Configuration.get_var(message.guild.id, "PREFIX"))
    return prefixes

def ready_bot


async def on_ready(bot: GearBot):
    if not bot.STARTUP_COMPLETE:
        GearbotLogging.initialize_pump(bot)
        await GearbotLogging.onReady(bot, Configuration.get_master_var("BOT_LOG_CHANNEL"))
        info = await bot.application_info()
        await GearbotLogging.bot_log(message="Spinning up the gears!")
        await Util.readyBot(bot)
        Emoji.on_ready(bot)
        Utils.on_ready(bot)
        Translator.on_ready(bot)
        bot.loop.create_task(keepDBalive(bot)) # ping DB every hour so it doesn't run off

        #shutdown handler for clean exit on linux
        try:
            for signame in ('SIGINT', 'SIGTERM'):
                asyncio.get_event_loop().add_signal_handler(getattr(signal, signame),
                                        lambda: asyncio.ensure_future(Utils.cleanExit(bot, signame)))
        except Exception:
            pass #doesn't work on windows

        bot.aiosession = aiohttp.ClientSession()
        bot.start_time = datetime.datetime.utcnow()
        GearbotLogging.info("Loading cogs...")
        for extension in Configuration.get_master_var("COGS"):
            try:
                bot.load_extension("Cogs." + extension)
            except Exception as e:
                GearbotLogging.exception(f"Failed to load extention {extension}", e)
        GearbotLogging.info("Cogs loaded")

        if Configuration.get_master_var("CROWDIN_KEY") is not None:
            bot.loop.create_task(translation_task(bot))

        await DocUtils.update_docs(bot)

        bot.STARTUP_COMPLETE = True
        await GearbotLogging.bot_log(message=f"All gears turning at full speed, {info.name} ready to go!")
        await bot.change_presence(activity=discord.Activity(type=3, name='the gears turn'))
    else:
        await bot.change_presence(activity=discord.Activity(type=3, name='the gears turn'))