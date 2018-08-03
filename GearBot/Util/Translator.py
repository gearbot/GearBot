import json
import os

from Util import Configuration

LANGS = dict()


def on_ready():
    directory = os.fsencode("lang")
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if filename.endswith(".json"):
            with open(f"lang/{filename}") as lang:
                LANGS[filename[:-5]] = json.load(lang)


def translate(key, location, **kwargs):
    if location is not None:
        if hasattr(location, "guild"):
            location = location.guild
        if location is not None and hasattr(location, "id"):
            lang_key = Configuration.getConfigVar(location.id, "LANG")
        else:
            lang_key = Configuration.getConfigVar(location, "LANG")
    else:
        lang_key = "en_US"
    if key in LANGS[lang_key].keys():
        return LANGS[lang_key][key].format(**kwargs)
    else:
        return key
