import asyncio
import hashlib
import json
import os
import shutil
import threading
import zipfile

from ruamel.yaml import YAML

yaml = YAML()

import aiohttp
import requests
from parsimonious import ParseError, VisitationError
from pyseeyou import format

from Util import Configuration, GearbotLogging, Emoji

LANGS = dict()
BOT = None
untranlatable = {"Sets a playing/streaming/listening/watching status", "Reloads all server configs from disk", "Reset the cache", "Make a role pingable for announcements", "Pulls from github so an upgrade can be performed without full restart"}

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
    translated = key
    if key not in LANGS[lang_key]:
        if key not in untranlatable:
            BOT.loop.create_task(tranlator_log('WARNING', f'Untranslatable string detected: {key}\n'))
            untranlatable.add(key)
        return key
    try:
        translated = format(LANGS[lang_key][key], kwargs, lang_key)
    except (KeyError, ValueError, ParseError, VisitationError) as ex:
        BOT.loop.create_task(tranlator_log('NO', f'Corrupt translation detected!\n**Lang code:** {lang_key}\n**Translation key:** {key}\n```\n{LANGS[lang_key][key]}```'))
        GearbotLogging.error(ex)
        if key in LANGS["en_US"].keys():
            try:
                translated = format(LANGS['en_US'][key], kwargs, 'en_US')
            except (KeyError, ValueError, ParseError, VisitationError) as ex:
                BOT.loop.create_task(tranlator_log('NO', f'Corrupt English source string detected!\n**Translation key:** {key}\n```\n{LANGS["en_US"][key]}```'))
                GearbotLogging.error(ex)
    GearbotLogging.info(f"Translated {key} to {lang_key}")
    return translated


def translate_by_code(key, code, **kwargs):
    return format(LANGS[code][key], kwargs, code)

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

                        #bot lang files
                        for f in os.listdir("temp/bot/"):
                            if os.path.isdir(f):
                                continue
                            os.rename(os.path.abspath(f"temp/bot/{f}"), os.path.abspath(f"lang/{f[-10:]}"))

                        #website translations
                        root = Configuration.get_master_var("WEBSITE_ROOT", "")
                        dirs = get_dir_tree("temp/docs/pages")

                        codes = list()
                        codes.append("en_US")
                        for dir in dirs:
                            dir = dir.replace("temp/docs/pages", "")
                            shutil.rmtree(f"{root}/pages/{dir}", ignore_errors=True)
                            os.makedirs(f"{root}/pages/{dir}")
                            name = "home" if "home" in dir else "doc"
                            o = os.path.abspath(f"docs/pages/{dir}/{name}.md")
                            shutil.copyfile(o, f"{root}/pages/{dir}/{name}.en_US.md")

                            original = hashlib.md5(open(o, 'rb').read()).hexdigest()
                            for file in os.listdir(f"temp/docs/pages/{dir}"):
                                p = f"temp/docs/pages/{dir}/{file}"
                                if os.path.isdir(p):
                                    continue
                                translated = hashlib.md5(open(p, 'rb').read()).hexdigest()
                                if translated == original:
                                    continue
                                code = file[-8:-3]
                                if code not in codes:
                                    codes.append(code)
                                os.rename(os.path.abspath(p), f"{root}/pages/{dir}/{file}")
                        config = f"{root}/config/system.yaml"
                        with open(config) as f:
                            c = yaml.load(f)
                        c["languages"]["supported"] = codes
                        with open(config, "w") as f:
                            yaml.dump(c, f)


                    load_translations()
                    await message.edit(content=f"{Emoji.get_chat_emoji('YES')} Translations have been updated")
            else:
                await message.edit(content=f"{Emoji.get_chat_emoji('WARNING')} Crowdin build status was `{response['success']['status']}`, no translation update required")

def get_targets():
    return get_content("docs/pages")

def get_content(base):
    targets = []
    for f in os.listdir(base):
        if os.path.isdir(f"{base}/{f}"):
            targets.extend(get_content(f"{base}/{f}"))
        else:
            targets.append(f"{base}/{f}")
    return targets


def get_dir_tree(base):
    targets = []
    for f in os.listdir(base):
        if os.path.isdir(f"{base}/{f}"):
            targets.append(f"{base}/{f}")
            targets.extend(get_dir_tree(f"{base}/{f}"))
    return targets

print(get_targets())

async def upload():
    if Configuration.get_master_var("CROWDIN", None) is None:
        return
    hashes = Configuration.get_persistent_var('hashes', {})

    targets = get_targets()
    target = "lang/en_US.json"
    new = hashlib.md5(open(target, 'rb').read()).hexdigest()
    old = hashes.get(target, "")
    if old != new:
        message = await tranlator_log('REFRESH', 'Uploading bot translation file')
        t = threading.Thread(target=upload_files, args=([("lang/en_US.json", "bot/commands.json", {"title": "GearBot bot strings", "export_pattern": "/bot/%locale_with_underscore%.json"}), False]))
        t.start()
        while t.is_alive():
            await asyncio.sleep(1)
        await message.edit(
            content=f"{Emoji.get_chat_emoji('YES')} Bot translation file has been uploaded")


    count = 0
    to_update = list()
    to_add = list()
    for target in targets:
        new = hashlib.md5(open(target, 'rb').read()).hexdigest()
        old = hashes.get(target, "")
        if old == new:
            continue
        count += 1
        hashes[target] = new
        title = None
        with open(target, 'r') as file:
            for line in file.readlines(10):
                if line.startswith("title = "):
                    title = line[8:]
                    break
        name = "home" if "home" in target else "doc"
        (to_add if old == "" else to_update).append((target, target, {"title": title, "export_pattern": f"/%original_path%/{name}.%locale_with_underscore%.md"}))
    message = await tranlator_log('REFRESH', 'Uploading website files')
    if len(to_add) > 0:
        t2 = threading.Thread(target=upload_files, args=(to_add, True))
        t2.start()
        while t2.is_alive():
            await asyncio.sleep(1)
    if len(to_update) > 0:
        t = threading.Thread(target=upload_files, args=(to_update, False))
        t.start()
        while t.is_alive():
            await asyncio.sleep(1)

    await message.edit(content=f"{Emoji.get_chat_emoji('YES')} {count} {'file has' if count == 1 else 'files have'} been updated")
    if count > 0:
        await update()
        Configuration.set_persistent_var('hashes', hashes)

def upload_files(target_info, new):
    crowdin_data = Configuration.get_master_var("CROWDIN")
    data = dict()
    if new:
        for l, o, e in target_info:
            data["name"] = "/".join(o.split("/")[:-1])
            data["recursive"] = "1"
            response = requests.post(f"https://api.crowdin.com/api/project/gearbot/add-directory?login={crowdin_data['login']}&account-key={crowdin_data['key']}&json", data=data)
            GearbotLogging.info(response.content)
    data = dict()
    data2 = dict()
    for local, online, extra in target_info:
        data[f'files[{online}]'] =  open(local, 'r')
        for k, v in extra.items():
            data2[f'{k}s[{online}]'] = v
    response = requests.post(f"https://api.crowdin.com/api/project/gearbot/{'add-file' if new else 'update-file'}?login={crowdin_data['login']}&account-key={crowdin_data['key']}&json", files=data, data=data2)
    GearbotLogging.info(response.content)

async def tranlator_log(emoji, message):
    crowdin = Configuration.get_master_var("CROWDIN")
    channel = BOT.get_channel(crowdin["CHANNEL"]) if crowdin is not None else None
    m = f'{Emoji.get_chat_emoji(emoji)} {message}'
    if channel is not None:
        return await channel.send(m)
    else:
        return await GearbotLogging.bot_log(m)