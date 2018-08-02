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


def translate(key, server, **kwargs):
    return LANGS[Configuration.getConfigVar(server, "LANG")][key].format(**kwargs)