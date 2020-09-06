import asyncio
import hashlib
import json
import threading

import urllib.parse
import requests
from parsimonious import ParseError, VisitationError
from pyseeyou import format

from Util import Configuration, GearbotLogging, Emoji, Utils

LANGS = dict()
LANG_NAMES = dict(en_US= "English")
LANG_CODES = dict(English="en_US")
BOT = None
untranlatable = {"Sets a playing/streaming/listening/watching status", "Reloads all server configs from disk", "Reset the cache", "Make a role pingable for announcements", "Pulls from github so an upgrade can be performed without full restart", ''}

async def initialize(bot_in):
    global BOT
    BOT = bot_in
    await load_codes()
    await update_all()
    for lang in LANG_CODES.values():
        load_translations(lang)

def load_translations(lang):
    LANGS[lang] = Utils.fetch_from_disk(f"lang/{lang}")

def translate(key, location, **kwargs):
    lid = None
    if location is not None:
        if hasattr(location, "guild"):
            location = location.guild
        if location is not None and hasattr(location, "id"):
            lid = location.id
        else:
            lid = location

    if lid is None:
        lang_key = "en_US"
    else:
        lang_key = Configuration.get_var(lid, "GENERAL", "LANG")
    translated = key
    if key not in LANGS[lang_key]:
        if key not in untranlatable:
            BOT.loop.create_task(tranlator_log('WARNING', f'Untranslatable string detected in {lang_key}: {key}\n'))
            untranlatable.add(key)
        return key if key not in LANGS["en_US"] else format(LANGS['en_US'][key], kwargs, 'en_US')
    try:
        translated = format(LANGS[lang_key][key], kwargs, lang_key)
    except (KeyError, ValueError, ParseError, VisitationError) as ex:
        BOT.loop.create_task(tranlator_log('NO', f'Corrupt translation detected!\n**Lang code:** {lang_key}\n**Translation key:** {key}\n```\n{LANGS[lang_key][key]}```'))
        GearbotLogging.exception("Corrupt translation", ex)
        if key in LANGS["en_US"].keys():
            try:
                translated = format(LANGS['en_US'][key], kwargs, 'en_US')
            except (KeyError, ValueError, ParseError, VisitationError) as ex:
                BOT.loop.create_task(tranlator_log('NO', f'Corrupt English source string detected!\n**Translation key:** {key}\n```\n{LANGS["en_US"][key]}```'))
                GearbotLogging.exception('Corrupt translation', ex)
    return translated


def translate_by_code(key, code, **kwargs):
    if key not in LANGS[code]:
        return key
    return format(LANGS[code][key], kwargs, code)


async def upload():
    t_info = Configuration.get_master_var("TRANSLATIONS", dict(SOURCE="SITE", CHANNEL=0, KEY="", LOGIN="", WEBROOT=""))
    if t_info["SOURCE"] == "DISABLED": return
    new = hashlib.md5(open(f"lang/en_US.json", 'rb').read()).hexdigest()
    old = Configuration.get_persistent_var('lang_hash', '')
    if old == new:
        return
    Configuration.set_persistent_var('lang_hash', new)
    message = await tranlator_log('REFRESH', 'Uploading translation file')
    t = threading.Thread(target=upload_file)
    t.start()
    while t.is_alive():
        await asyncio.sleep(1)
    await message.edit(content=f"{Emoji.get_chat_emoji('YES')} Translations file has been uploaded")
    await update_all()


def upload_file():
    data = {'files[/bot/commands.json]': open('lang/en_US.json', 'r')}
    crowdin_data = Configuration.get_master_var("TRANSLATIONS", dict(SOURCE="SITE", CHANNEL=0, KEY= "", LOGIN="", WEBROOT=""))
    reply = requests.post(f"https://api.crowdin.com/api/project/gearbot/update-file?login={crowdin_data['LOGIN']}&account-key={crowdin_data['KEY']}&json", files=data)
    GearbotLogging.info(reply)


async def load_codes():
    t_info = Configuration.get_master_var("TRANSLATIONS", dict(SOURCE="SITE", CHANNEL=0, KEY= "", LOGIN="", WEBROOT=""))
    if t_info["SOURCE"] == "DISABLED": return
    GearbotLogging.info(f"Getting all translations from {t_info['SOURCE']}...")
    # set the links for where to get stuff
    if t_info["SOURCE"] == "CROWDIN":
        list_link = f"https://api.crowdin.com/api/project/gearbot/status?login={t_info['LOGIN']}&account-key={t_info['KEY']}&json"
    else:
        list_link = "https://gearbot.rocks/lang/langs.json"

    async with BOT.aiosession.get(list_link) as resp:
        info = await resp.json()
        l = list()
        for lang in info:
            l.append(dict(name=lang["name"], code=lang["code"]))
            LANG_NAMES[lang["code"]] = lang["name"]
            LANG_CODES[lang["name"]] = lang["code"]
        Utils.save_to_disk("lang/langs", l)

async def update_all():
    futures = [update_lang(lang) for lang in LANG_CODES.values() if lang != "en_US"]
    for chunk in Utils.chunks(futures, 20):
        await asyncio.gather(*chunk)


async def update_lang(lang, retry=True):
    t_info = Configuration.get_master_var("TRANSLATIONS")
    if t_info["SOURCE"] == "DISABLED": return
    if t_info["SOURCE"] == "CROWDIN":
        download_link = f"https://api.crowdin.com/api/project/gearbot/export-file?login={t_info['LOGIN']}&account-key={t_info['KEY']}&json&file={urllib.parse.quote('/bot/commands.json', safe='')}&language={lang}"
    else:
        download_link = f"https://gearbot.rocks/lang/{lang}.json"
    GearbotLogging.info(f"Updating {lang} ({LANG_NAMES[lang]}) file...")
    async with BOT.aiosession.get(download_link) as response:
        content = await response.text()
        content = json.loads(content)
        if "success" in content:
            if retry:
                GearbotLogging.warn(f"Failed to update {lang} ({LANG_NAMES[lang]}), trying again in 3 seconds")
                await asyncio.sleep(3)
                await update_lang(lang, False)
            else:
                await tranlator_log('NO', f"Failed to update {lang} ({LANG_NAMES[lang]}) from {t_info['SOURCE']}")
        Utils.save_to_disk(f'lang/{lang}', content)
        LANGS[lang] = content
        GearbotLogging.info(f"Updated {lang} ({LANG_NAMES[lang]})!")


async def tranlator_log(emoji, message, embed=None):
    m = f'{Emoji.get_chat_emoji(emoji)} {message}'
    return await get_translator_log_channel()(m, embed=embed)

def get_translator_log_channel():
    crowdin = Configuration.get_master_var("TRANSLATIONS", dict(SOURCE="SITE", CHANNEL=0, KEY= "", LOGIN="", WEBROOT=""))
    channel = BOT.get_channel(crowdin["CHANNEL"]) if crowdin is not None else None
    return channel.send if channel is not None else GearbotLogging.bot_log