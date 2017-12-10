import json

import discord

from Util import configuration
from commands.RoleCommands import RoleCommand
from distutils.version import LooseVersion

versions:dict = dict()

def initVersionInfo():
    try:
        with open('versions.json', 'r') as jsonfile:
            global versions
            versions = json.load(jsonfile)
    except FileNotFoundError:
        saveVersionInfo()
        initVersionInfo()
    except Exception as e:
        print(e)
        raise e

def saveVersionInfo():
    global versions
    with open('versions.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(versions, indent=4, skipkeys=True, sort_keys=True)))

def compareVersions(v1, v2):
    return LooseVersion(v1) > LooseVersion(v2)

def cmp_to_key(mycmp):
    'Convert a cmp= function into a key= function'
    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K

def getSortedVersions():
    return sorted(list(versions.keys()), key=cmp_to_key(compareVersions))


class addVersion(RoleCommand):
    """Adds a new BC release"""

    def __init__(self):
        super().__init__()
        self.extraHelp["params"] = "Minecraft version\nBuildcraft version\nBlog post link"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        global versions
        if not len(params) == 3:
            await client.send_message(channel, "Invalid params")
            return
        MCVersion = params[0]
        BCVersion = params[1]
        blogLink = params[2]
        if not MCVersion in versions.keys():
            versions[MCVersion] = dict()
            await client.send_message(channel, "I didn't know that MC version existed, yet, now i do!")
        versions[MCVersion]["BC_VERSION"] = BCVersion
        versions[MCVersion]["BLOG_LINK"] = blogLink
        saveVersionInfo()

        return

    def onReady(self, client: discord.Client):
        initVersionInfo()
        self.role = configuration.getConfigVar("DEV_ROLE_ID")