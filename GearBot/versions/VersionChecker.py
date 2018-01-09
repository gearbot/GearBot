import asyncio
import datetime
import json
import logging
import time
import traceback
import urllib.request

import discord

import Variables
from Util import configuration

BC_VERSION_LIST = {}
BCC_VERSION_LIST = {}
BCT_VERSION_LIST = {}
LAST_UPDATE = 0
ALLOWED_TO_ANNOUNCE = True
VERSIONS_PER_MC_VERSION = {}


async def runVersionChecker(client:discord.Client):
    try:
        global LAST_UPDATE, ALLOWED_TO_ANNOUNCE, VERSIONS_PER_MC_VERSION
        while not client.is_closed:
            newBC = 0
            newBCC = 0
            newBCT = 0
            newBClist = {}
            newBCClist = {}
            newBCTlist = {}
            logging.info("Version check initiated")
            timestamp = int(await getFileContent("https://www.mod-buildcraft.com/build_info_full/last_change.txt"))
            prevChange = LAST_UPDATE
            logging.info(timestamp)
            if timestamp > prevChange:
                logging.info("Timestamp updated, on to finding the new things")
                LAST_UPDATE = timestamp
                logging.info("Fetching BuildCraft releases")
                content = await getFileContent("https://www.mod-buildcraft.com/build_info_full/BuildCraft/versions.txt")
                versionlistBC = content.decode("utf-8").split("\n")[:-1] #strip last empty entry
                newBC = len(versionlistBC) - len(BC_VERSION_LIST)
                logging.info(f"found {len(versionlistBC)} BuildCraft releases, {newBC} new")
                if newBC > 0:
                    for version in versionlistBC:
                        if not version in BC_VERSION_LIST.keys():
                            logging.info(f"New BuildCraft release detected: {version}")
                            try:
                                with urllib.request.urlopen(f"https://www.mod-buildcraft.com/build_info_full/BuildCraft/{version}.json") as inforequest:
                                    info = json.load(inforequest)
                                    if not "mc_version" in info.keys():
                                        # no info, set to dummy
                                        info["mc_version"] = "Unknown"
                                    if not "forge_version" in info.keys():
                                        info["forge_version"] = "Unknown"
                                BC_VERSION_LIST[version] = info
                                newBClist[version] = info
                            except Exception as ex:
                                logging.error(f"Failed to fetch info for BuildCraft {version}")
                            await asyncio.sleep(0.1)


                content = await getFileContent("https://www.mod-buildcraft.com/build_info_full/BuildCraftCompat/versions.txt")
                versionlistBCC = content.decode("utf-8").split("\n")[:-1]
                newBCC = len(versionlistBCC) - len(BCC_VERSION_LIST)
                logging.info(f"found {len(versionlistBCC)} BuildCraft Compat releases, {newBCC} new")
                if newBCC > 0:
                    for version in versionlistBCC:
                        if not version in BCC_VERSION_LIST.keys():
                            logging.info(f"New Buildcraft Compat release detected: {version}")
                            try:
                                with urllib.request.urlopen(f"https://www.mod-buildcraft.com/build_info_full/BuildCraftCompat/{version}.json") as inforequest:
                                    info = json.load(inforequest)
                                    if not "mc_version" in info.keys():
                                        # no info, set to dummy
                                        info["mc_version"] = "Unknown"
                                BCC_VERSION_LIST[version] = info
                                newBCClist[version] = info
                            except Exception as ex:
                                logging.error(f"Failed to fetch info for BuildCraft Compat {version}")
                            await asyncio.sleep(0.1)



                content = await getFileContent("https://www.mod-buildcraft.com/build_info_full/testing/BuildCraft/versions.txt")
                versionlistBCT = content.decode("utf-8").split("\n")[:-1]
                newBCT = len(versionlistBCT) - len(BCT_VERSION_LIST)
                logging.info(f"found {len(versionlistBCT)} BuildCraft pre-releases, {newBCT} new")
                if newBCT > 0:
                    for version in versionlistBCT:
                        if not version in BCT_VERSION_LIST.keys():
                            logging.info(f"New Buildcraft Compat release detected: {version}")
                            try:
                                with urllib.request.urlopen(f"https://www.mod-buildcraft.com/build_info_full/testing/BuildCraft/{version}.json") as inforequest:
                                    info = json.load(inforequest)
                                    if not "mc_version" in info.keys():
                                        # no info, set to dummy
                                        info["mc_version"] = "Unknown"
                                    if not "forge_version" in info.keys():
                                        info["forge_version"] = "Unknown"
                                BCT_VERSION_LIST[version] = info
                                newBCTlist[version] = info
                            except Exception as ex:
                                logging.error(f"Failed to fetch info for BuildCraft Testing {version}")
                            await asyncio.sleep(0.1)

            sorted = processVersions(newBClist, newBCClist)
            await asyncio.sleep(0.1)
            if (ALLOWED_TO_ANNOUNCE):
                if newBC + newBCC > 0:
                    embed = discord.Embed(title=f"I found {newBC + newBCC} new releases!", color=0x66E2CE, timestamp=datetime.datetime.utcfromtimestamp(time.time()))
                    embed.set_thumbnail(url="https://i.imgur.com/nYVf16P.png")
                    blogpost = None
                    for version, versions in sorted.items():
                        infostring = ""
                        for BCVersion in versions["BC"]:
                            infostring = infostring + f"Buildcraft {BCVersion}\n"
                            if blogpost is None and 'blog_entry' in newBClist[BCVersion].keys():
                                blogpost = newBClist[BCVersion]['blog_entry']
                        for BCCVersion in versions["BCC"]:
                            infostring = infostring + f"Buildcraft Compat {BCCVersion}\n"
                            if blogpost is None and 'blog_entry' in newBCClist[BCCVersion].keys():
                                blogpost = newBCClist[BCCVersion]['blog_entry']
                        embed.add_field(name=f"Minecraft {version}", value=infostring)
                    if not blogpost is None:
                        embed.add_field(name="More info", value=f"[Blog post]({blogpost})")
                    await client.send_message(Variables.ANNOUNCEMENTS_CHANNEL, embed=embed)
                    await asyncio.sleep(0.1)
                for version, info in newBCTlist.items():
                    server = discord.utils.get(client.servers, id=configuration.getConfigVar(
                        "MAIN_SERVER_ID"))
                    role = discord.utils.get(server.roles, id=configuration.getConfigVar("TESTER_ROLE_ID"))
                    embed = discord.Embed(title="I found a new pre-release!", color=0x865F32, timestamp=datetime.datetime.utcfromtimestamp(time.time()), description=f"Version: {version}\nMC version: {info['mc_version']}\n[Download]({info['downloads']['main']}) | [More info](https://www.mod-buildcraft.com/pages/tests.html)")
                    embed.set_thumbnail(url="https://i.imgur.com/UcyDPBe.png")
                    await client.edit_role(server, role, mentionable=True)
                    await client.send_message(Variables.TESTING_CHANNEL, f"<@&{configuration.getConfigVar('TESTER_ROLE_ID')}>", embed=embed)
                    await client.edit_role(server, role, mentionable=False)
                    await asyncio.sleep(0.1)

            if newBC + newBCC + newBCT > 0:
                embed = discord.Embed(title=f"Version check complete, {newBC + newBCC + newBCT} new releases detected", timestamp=datetime.datetime.utcfromtimestamp(time.time()))
                for version, versions in sorted.items():
                    embed.add_field(name=version, value=f"BuildCraft relseases:\t\t\t\t\t{len(versions['BC'])}\nBuildCraft Compat releases:\t {len(versions['BCC'])}\t")
                await client.send_message(Variables.BOT_LOG_CHANNEL, embed=embed)
                await asyncio.sleep(0.1)
            saveVersions()
            ALLOWED_TO_ANNOUNCE = True
            await asyncio.sleep(0.1)
            VERSIONS_PER_MC_VERSION = processVersions(BC_VERSION_LIST, BCC_VERSION_LIST)
            await asyncio.sleep(600)
    except Exception as ex:
        logging.error("Version check execution failed, bot restart required:"
                      f"    Exception: {ex}")
        try:
            embed = discord.Embed(colour=discord.Colour(0xff0000),
                                  timestamp=datetime.datetime.utcfromtimestamp(time.time()))

            embed.set_author(name="Version check execution failed, bot restart required")

            embed.add_field(name="Exception", value=ex)
            embed.add_field(name="Stacktrace", value=traceback.format_exc())

            await Variables.DISCORD_CLIENT.send_message(Variables.BOT_LOG_CHANNEL, embed=embed)
        except Exception as ex:
            logging.error("Failed to log exception to discord")

def assembleVersionString(info):
    infostring = f"Minecraft version:\t{info['mc_version']}\n"
    if "forge_version" in info.keys():
        infostring = infostring + f"Forge version:\t{info['forge_version']}\n"
    if "blog_entry" in info.keys():
        infostring = infostring + f"[Blog]({info['blog_entry']}) | "
    infostring = infostring + f"[Direct download]({info['downloads']['main']})\n\u200b"
    return infostring

async def getFileContent(url):
    with urllib.request.urlopen(url) as request:
        content = request.read()
    await asyncio.sleep(0.1)
    return content

def loadVersions():
    global BC_VERSION_LIST, BCC_VERSION_LIST, BCT_VERSION_LIST, ALLOWED_TO_ANNOUNCE, LAST_UPDATE, VERSIONS_PER_MC_VERSION
    try:
        with open('versioninfo.json', 'r') as jsonfile:
            info = json.load(jsonfile)
            BC_VERSION_LIST = info["BC_VERSION_LIST"]
            BCC_VERSION_LIST = info["BCC_VERSION_LIST"]
            BCT_VERSION_LIST = info["BCT_VERSION_LIST"]
            LAST_UPDATE = info["LAST_UPDATE"]
            VERSIONS_PER_MC_VERSION = processVersions(BC_VERSION_LIST, BCC_VERSION_LIST)
    except FileNotFoundError:
        logging.error("Unable to load version info, did the cache get cleared? No new versions will be announced during next version checking")
        ALLOWED_TO_ANNOUNCE = False
    except Exception as e:
        logging.error("Failed to parse version info")
        print(e)
        raise e

def saveVersions():
    with open('versioninfo.json', 'w') as jsonfile:
        jsonfile.write((json.dumps({"BC_VERSION_LIST": BC_VERSION_LIST,
                                    "BCC_VERSION_LIST": BCC_VERSION_LIST,
                                    "BCT_VERSION_LIST": BCT_VERSION_LIST,
                                    "LAST_UPDATE": LAST_UPDATE
                                    }, indent=4, skipkeys=True, sort_keys=True)))


def init(client):
    loadVersions()
    client.loop.create_task(runVersionChecker(client))

def processVersions(BC, BCC):
    sorted = {}
    for version, info in BC.items():
        if info["mc_version"] == "Unknown":
            continue
        if not info["mc_version"] in sorted.keys():
            sorted[info["mc_version"]] = {"BC": [], "BCC": []}
        sorted[info["mc_version"]]["BC"].append(version)
    for version, info in BCC.items():
        if not info["mc_version"] in sorted.keys():
            sorted[info["mc_version"]] = {"BC": [], "BCC": []}
        sorted[info["mc_version"]]["BCC"].append(version)
    return sorted
