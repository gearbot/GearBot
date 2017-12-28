import asyncio
import logging
import urllib.request
import json

from Util import configuration

BC_VERSION_LIST = {}
BCC_VERSION_LIST = {}
BCT_VERSION_LIST = {}

async def runVersionChecker():
    while True:#not client.is_closed:
        logging.info("Version check initiated")
        timestamp = int(await getFileContent("https://www.mod-buildcraft.com/build_info_full/last_change.txt"))
        prevChange = configuration.getConfigVar("BC_INFO_LAST_CHANGE", 0)
        logging.info(timestamp)
        if timestamp > prevChange or True:
            logging.info("Timestamp updated, on to finding the new things")
            configuration.setConfigVar("BC_INFO_LAST_CHANGE", timestamp)
            logging.info("Fetching BuildCraft releases")
            content = await getFileContent("https://www.mod-buildcraft.com/build_info_full/BuildCraft/versions.txt")
            versionlistBC = content.decode("utf-8").split("\n")
            logging.info(f"found {len(versionlistBC)} BuildCraft releases")
            for version in versionlistBC:
                if not version == "" and not version in BC_VERSION_LIST.keys():
                    try:
                        with urllib.request.urlopen(f"https://www.mod-buildcraft.com/build_info_full/BuildCraft/{version}.json") as inforequest:
                            info = json.load(inforequest)
                            if not "mc_version" in info.keys():
                                # no info, set to dummy
                                info["mc_version"] = "Unknown"
                            # await asyncio.sleep(1)
                        BC_VERSION_LIST[version] = info
                    except Exception as ex:
                        logging.error(f"Failed to fetch info for {version}")

            content = await getFileContent("https://www.mod-buildcraft.com/build_info_full/BuildCraftCompat/versions.txt")
            versionlistBCC = content.decode("utf-8").split("\n")
            logging.info(f"found {len(versionlistBCC)} BuildCraft Compat releases")
            content = await getFileContent("https://www.mod-buildcraft.com/build_info_full/testing/BuildCraft/versions.txt")
            versionlistBCT = content.decode("utf-8").split("\n")
            logging.info(f"found {len(versionlistBCT)} BuildCraft pre-releases")



        await asyncio.sleep(8)

async def getFileContent(url):
    with urllib.request.urlopen(url) as request:
        content = request.read()
    #await asyncio.sleep(1)
    return content

from logging import INFO
logging.basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")

configuration.loadconfig()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop = asyncio.get_event_loop()
loop.run_until_complete(runVersionChecker())
loop.close()