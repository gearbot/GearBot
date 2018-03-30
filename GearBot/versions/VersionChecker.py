import asyncio
import datetime
import json
import logging
import time
import traceback
import urllib.request

import discord

import Variables
from Util import Configuration, GearbotLogging
from versions import VersionInfo

BC_VERSION_LIST = {}
BCC_VERSION_LIST = {}
BCT_VERSION_LIST = {}
BCCT_VERSION_LIST = {}
LAST_UPDATE = 0
ALLOWED_TO_ANNOUNCE = True
VERSIONS_PER_MC_VERSION = {}


def init(client):
    loadVersions()
    client.loop.create_task(runVersionChecker(client))

def loadVersions():
    global BC_VERSION_LIST, BCC_VERSION_LIST, BCT_VERSION_LIST, ALLOWED_TO_ANNOUNCE, LAST_UPDATE, VERSIONS_PER_MC_VERSION, BCCT_VERSION_LIST
    try:
        with open('versioninfo.json', 'r') as jsonfile:
            info = json.load(jsonfile)
            BC_VERSION_LIST = info["BC_VERSION_LIST"]
            BCC_VERSION_LIST = info["BCC_VERSION_LIST"]
            BCT_VERSION_LIST = info["BCT_VERSION_LIST"]
            BCCT_VERSION_LIST = info["BCCT_VERSION_LIST"]
            LAST_UPDATE = info["LAST_UPDATE"]
            VERSIONS_PER_MC_VERSION = processVersions(BC_VERSION_LIST, BCC_VERSION_LIST)
    except FileNotFoundError:
        logging.error("Unable to load version info, did the cache get cleared? No new versions will be announced during next version checking")
        ALLOWED_TO_ANNOUNCE = False
    except Exception as e:
        logging.error("Failed to parse version info")
        print(e)
        raise e


async def runVersionChecker(client:discord.Client):
    try:
        global LAST_UPDATE, ALLOWED_TO_ANNOUNCE, VERSIONS_PER_MC_VERSION
        while not client.is_closed:
            logging.info("Version check initiated")
            timestamp = int(await getFileContent("https://www.mod-buildcraft.com/build_info_full/last_change.txt"))
            prevChange = LAST_UPDATE
            if timestamp > prevChange:
                logging.info("Timestamp updated, on to finding the new things")
                LAST_UPDATE = timestamp
                logging.info("Fetching BuildCraft releases")

                newBClist, removed = await getVersionList("BuildCraft", BC_VERSION_LIST)
                newBCClist, removed = await getVersionList("BuildCraftCompat", BCC_VERSION_LIST)
                newBCTlist, removedBCT = await getVersionList("testing/BuildCraft", BCT_VERSION_LIST)
                newBCCTlist, removedBCCT = await getVersionList("testing/BuildCraftCompat", BCCT_VERSION_LIST)

                sorted = processVersions(newBClist, newBCClist)
                await asyncio.sleep(0)

                if ALLOWED_TO_ANNOUNCE:
                    await announceNewVersions(sorted, newBClist, newBCClist, client)

                    shouldMention = True
                    shouldMention = await handleNewTestReleases(newBCTlist, removedBCT, "BuildCraft", client, shouldMention)
                    await handleNewTestReleases(newBCCTlist, removedBCCT, "BuildCraft Compat", client, shouldMention)

                    await logNewVersions(newBClist, newBCClist, newBCTlist, newBCCTlist, sorted, client)

                saveVersions()
                ALLOWED_TO_ANNOUNCE = True
                await asyncio.sleep(0)
                VERSIONS_PER_MC_VERSION = processVersions(BC_VERSION_LIST, BCC_VERSION_LIST)
            await asyncio.sleep(600)
    except Exception as ex:
        logging.error("Version check execution failed!"
                      f"    Exception: {ex}")
        logging.error(traceback.format_exc())
        try:
            embed = discord.Embed(colour=discord.Colour(0xff0000),
                                  timestamp=datetime.datetime.utcfromtimestamp(time.time()))

            embed.set_author(name="Version check execution failed!")

            embed.add_field(name="Exception", value=str(ex))
            embed.add_field(name="Stacktrace", value=traceback.format_exc())

            await Variables.DISCORD_CLIENT.send_message(Variables.BOT_LOG_CHANNEL, embed=embed)
        except Exception as ex:
            logging.error("Failed to log exception to discord")

async def getVersionList(link, list):
    added = {}
    removed = {}
    errorstring = ""
    try:
        content = await getFileContent(f"https://www.mod-buildcraft.com/build_info_full/{link}/versions.txt")
        versionlist = content.decode("utf-8").split("\n")[:-1]
        for v in versionlist:
            if not v in list.keys():
                try:
                    with urllib.request.urlopen(f"https://www.mod-buildcraft.com/build_info_full/{link}/{v}.json") as inforequest:
                        info = json.load(inforequest)
                        if not "mc_version" in info.keys():
                            # no info, set to dummy
                            info["mc_version"] = "Unknown"
                        if not "forge_version" in info.keys():
                            info["forge_version"] = "Unknown"
                        list[v] = info
                        added[v] = info
                        logging.info(f"New {link} release: {v}")
                except Exception as ex:
                    errorstring = f"{errorstring}Failed to get info for {link} release {v}\n"
            await asyncio.sleep(0)
        for v in list.keys():
            if not v in versionlist:
                if link.startswith("testing"):
                    removed[v] = list[v]
                    logging.info(f"{link} release removed: {v}")
                else:
                    errorstring = f"{errorstring}ERROR: {link} {v} release went missing!\n"
        for v in removed.keys():
            del list[v]

    except Exception as ex:
        if link.startswith("testing"):
            logging.info(f"Seems there are no more {link} versions, clearing")
            for v in list.keys():
                removed[v] = list[v]
            for v in removed.keys():
                del list[v]
        else:
            logging.error(f"Failed to fetch info for {link}")
            raise ex
    if len(errorstring) > 0:
        logging.error(errorstring)
        GearbotLogging.logToLogChannel(embed=discord.Embed(colour=discord.Colour(0xff0000),
                                                           timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                                           title="Versioncheck for {link} failure!",
                                                           description=errorstring))
        return {}, {}
    await asyncio.sleep(0)
    return added, removed

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
    await asyncio.sleep(0)
    return content

def saveVersions():
    with open('versioninfo.json', 'w') as jsonfile:
        jsonfile.write((json.dumps({"BC_VERSION_LIST": BC_VERSION_LIST,
                                    "BCC_VERSION_LIST": BCC_VERSION_LIST,
                                    "BCT_VERSION_LIST": BCT_VERSION_LIST,
                                    "BCCT_VERSION_LIST": BCCT_VERSION_LIST,
                                    "LAST_UPDATE": LAST_UPDATE
                                    }, indent=4, skipkeys=True, sort_keys=True)))

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

def assembleReleaseEmbed(type, version, info, blogpost):
    desc = f"Minecraft version: {info['mc_version']}\nMin forge version: {info['forge_version']}\n"
    if type == 'BuildCraft':
        desc = desc + f"[Changelog](https://www.mod-buildcraft.com/pages/buildinfo/BuildCraft/changelog/{version}.html) | "
    desc = desc + f"[Blog post]({blogpost}) | [Direct download]({info['downloads']['main']})"
    embed = discord.Embed(color=0x66E2CE, timestamp=datetime.datetime.utcfromtimestamp(time.time()), description=desc)
    embed.set_author(name=f"New {type} release: {version}", icon_url="https://i.imgur.com/nYVf16P.png")
    return embed

def findBlogPost(list):
    for mcv, lists in list.items():
        for v in lists['BC']:
            if 'blog_entry' in BC_VERSION_LIST[v].keys():
                return BC_VERSION_LIST[v]['blog_entry']
        for v in lists['BCC']:
            if 'blog_entry' in BCC_VERSION_LIST[v].keys():
                return BCC_VERSION_LIST[v]['blog_entry']
    return "https://www.mod-buildcraft.com/"


async def announceNewVersions(sorted, newBClist, newBCClist, client):
    blogpost = findBlogPost(sorted)
    for version, info in newBClist.items():
        message = await client.send_message(Variables.ANNOUNCEMENTS_CHANNEL,
                                            embed=assembleReleaseEmbed("BuildCraft", version, info, blogpost))
        info['messageID'] = message.id
        await asyncio.sleep(0)
    for version, info in newBCClist.items():
        message = await client.send_message(Variables.ANNOUNCEMENTS_CHANNEL,
                                            embed=assembleReleaseEmbed("BuildCraft Compat", version, info, blogpost))
        info['messageID'] = message.id
        await asyncio.sleep(0)
    latest = VersionInfo.getLatest(BC_VERSION_LIST)
    await client.edit_channel(Variables.GENERAL_CHANNEL,
                              topic=f"General discussions about BuildCraft. \nLatest version: {latest} \nFull changelog and download: {BC_VERSION_LIST[latest]['blog_entry']}")

async def handleNewTestReleases(new, removed, name, client, shouldMention):
    if len(new) > 0:
        server = discord.utils.get(client.servers, id=Configuration.getMasterConfigVar("MAIN_SERVER_ID"))
        role = discord.utils.get(server.roles, id=Configuration.getMasterConfigVar("TESTER_ROLE_ID"))
        await client.edit_role(server, role, mentionable=True)
        for version, info in new.items():
            embed = discord.Embed(title=f"I found a new {name} pre-release!", color=0x865F32,
                                  timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                  description=f"Version: {version}\nMC version: {info['mc_version']}\n[Download]({info['downloads']['main']}) | [More info](https://www.mod-buildcraft.com/pages/tests.html)")
            embed.set_thumbnail(url="https://i.imgur.com/UcyDPBe.png")
            message = await client.send_message(Variables.TESTING_CHANNEL,
                                                f"<@&{configuration.getMasterConfigVar('TESTER_ROLE_ID')}>" if shouldMention else None,
                                                embed=embed)
            shouldMention = False
            info['messageID'] = message.id
            await client.pin_message(message)
            await asyncio.sleep(0)
        await client.edit_role(server, role, mentionable=False)
        await asyncio.sleep(0)
    for version, info in removed.items():
        if 'messageID' in info.keys():
            await client.unpin_message(await client.get_message(Variables.TESTING_CHANNEL, info['messageID']))
    return shouldMention


async def logNewVersions(newBClist, newBCClist, newBCTlist, newBCCTlist, sorted, client):
    if len(newBClist) + len(newBCClist) + len(newBCTlist) + len(newBCCTlist) > 0:
        embed = discord.Embed(title=f"Version check complete, {len(newBClist) + len(newBCClist) + len(newBCTlist) + len(newBCCTlist)} new releases detected",
                              timestamp=datetime.datetime.utcfromtimestamp(time.time()))
        if len(newBClist) > 0:
            embed.add_field(name="BuildCraft", value=listVersions(newBClist))
        if len(newBCClist) > 0:
            embed.add_field(name="BuildCraft Compat", value=listVersions(newBCClist))
        if len(newBCTlist) > 0:
            embed.add_field(name="BuildCraft pre-releases", value=listVersions(newBCTlist))
        if len(newBCCTlist) > 0:
            embed.add_field(name="BuildCraft Compat pre-releases", value=listVersions(newBCCTlist))

        for version, versions in sorted.items():
            embed.add_field(name=version,
                            value=f"BuildCraft releases:\t\t\t\t\t{len(versions['BC'])}\nBuildCraft Compat releases:\t {len(versions['BCC'])}\t")
        await client.send_message(Variables.BOT_LOG_CHANNEL, embed=embed)
        await asyncio.sleep(0)

def listVersions(list):
    info = ""
    for v in list:
        info = f"{v}\n{info}"
    return info