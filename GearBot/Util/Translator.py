import asyncio
import hashlib
import json
import os
import shutil
import threading
import zipfile

import aiohttp
import requests
from parsimonious import ParseError, VisitationError
from pyseeyou import format

from Util import Configuration, GearbotLogging, Emoji

LANGS = dict()
BOT = None

def initialize(bot_in):
    global BOT
    BOT = bot_in
    load_translations()

def load_translations():
    directory = os.fsencode("lang")
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith(".json"):
            with open(f"lang/{filename}", encoding="UTF-8") as lang:
                LANGS[filename[:-5]] = json.load(lang)

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
        lang_key = Configuration.get_var(lid, "LANG")
    GearbotLogging.info(f"Translating {key} to {lang_key}")
    if key in LANGS[lang_key].keys():
        short_code = lang_key[:2]
    translated = key
    try:
        translated = format(LANGS[lang_key][key], kwargs, short_code)
    except (KeyError, ValueError, ParseError, VisitationError) as ex:
        BOT.loop.create_task(tranlator_log('NO', f'Corrupt translation detected!\n**Lang code:** {lang_key}\n**Translation key:** {key}\n```\n{LANGS[lang_key][key]}```'))
        GearbotLogging.error(ex)
    if key in LANGS["en_US"].keys():
        try:
            translated = format(LANGS['en_US'][key], kwargs, 'en')
        except (KeyError, ValueError, ParseError, VisitationError) as ex:
            BOT.loop.create_task(tranlator_log('NO', f'Corrupt English source string detected!\n**Translation key:** {key}\n```\n{LANGS["en_US"][key]}```'))
            GearbotLogging.error(ex)
    GearbotLogging.info(f"Finished translating {key} to {lang_key}")
    return traslated


async def update():
    message = await tranlator_log('REFRESH', 'Updating translations')
    crowdin_data = Configuration.get_master_var("CROWDIN")
    session: aiohttp.ClientSession = BOT.aiosession
    async with session.get(f"https://api.crowdin.com/api/project/Gearbot/export?login={crowdin_data['login']}&account-key={crowdin_data['key']}&json",) as reply:
        if reply.status is not 200:
            await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('WARNING')} Crowdin api error, got response code {reply.status}")
        else:
            response  = await reply.json()
            if response["success"]["status"] == "built": # only update translations if we actually got a new build, should be every time though unless this runs 2x within 30 mins for some reason
                async with session.get(
                        f"https://api.crowdin.com/api/project/Gearbot/download/all.zip?login={crowdin_data['login']}&account-key={crowdin_data['key']}") as reply:
                    data = await reply.read()
                    with open("zip.zip", "wb") as file:
                        file.write(data)
                    with zipfile.ZipFile("zip.zip", "r") as archive:
                        tempdir = os.path.abspath("temp")
                        if os.path.isdir(tempdir):
                            shutil.rmtree(tempdir, ignore_errors=True)
                        os.mkdir(tempdir)
                        archive.extractall("temp")
                        for entry in archive.filelist:
                            if not entry.filename.endswith(".json"):
                                continue
                            filename =entry.filename[-10:]
                            if os.path.isfile(os.path.abspath(f"lang/{filename}")):
                                os.remove(os.path.abspath(f"lang/{filename}"))
                            archive.extract(entry, tempdir)
                            os.rename(os.path.abspath(f"temp/{entry.filename}"), os.path.abspath(f"lang/{filename}"))
                            shutil.rmtree("temp", ignore_errors=True)
                    load_translations()
                    await message.edit(content=f"{Emoji.get_chat_emoji('YES')} Translations have been updated")
            else:
                await message.edit(content=f"{Emoji.get_chat_emoji('WARNING')} Crowdin build status was `{response['success']['status']}`, no translation update required")

async def upload():
    if Configuration.get_master_var("CROWDIN", None) is None:
        return

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
    await update()

def upload_file():
    data = {'files[master/lang/en_US.json]': open('lang/en_US.json', 'r')}
    crowdin_data = Configuration.get_master_var("CROWDIN")
    requests.post(f"https://api.crowdin.com/api/project/gearbot/update-file?login={crowdin_data['login']}&account-key={crowdin_data['key']}&json", files=data)

async def tranlator_log(emoji, message):
    channel = BOT.get_channel(Configuration.get_master_var("CROWDIN")["CHANNEL"])
    m = f'{Emoji.get_chat_emoji(emoji)} {message}'
    if channel is not None:
        return await channel.send(m)
    else:
        return GearbotLogging.bot_log(m)