import asyncio
import logging
import urllib.request

from Util import configuration

BC_VERSION_LIST = {}
BCC_VERSION_LIST = {}
BCT_VERSION_LIST = {}

async def runVersionChecker():
    while True:#not client.is_closed:
        logging.info("Version check initiated")
        with urllib.request.urlopen("https://www.mod-buildcraft.com/build_info_full/last_change.txt") as request:
            #await asyncio.sleep(1)  # sleep to have the bot loop continue from time to time, the url request might take time when connection is slow
            prevChange = configuration.getConfigVar("BC_INFO_LAST_CHANGE", 0)
            timestamp = int(request.read())
            logging.info(timestamp)
            if timestamp > prevChange or True:
                logging.info("Timestamp updated, on to finding the new things")
                configuration.setConfigVar("BC_INFO_LAST_CHANGE", timestamp)
                #await asyncio.sleep(1)
                logging.info("Fetching BuildCraft releases")
                with urllib.request.urlopen("https://www.mod-buildcraft.com/build_info_full/BuildCraft/versions.txt") as bcRequest:
                    content = bcRequest.read()
                    versionlistBC = str(content)[2:].split(r"\n")
                    for version in versionlistBC:
                        if not version in BC_VERSION_LIST.keys():
                            pass
                    logging.info(f"found {len(versionlistBC)} BuildCraft releases")
                with urllib.request.urlopen("https://www.mod-buildcraft.com/build_info_full/BuildCraftCompat/versions.txt") as bccRequest:
                    versionlistBCC = str(bccRequest.read())[2:].split(r"\n")
                    logging.info(f"found {len(versionlistBCC)} BuildCraft Compat releases")
                with urllib.request.urlopen("https://www.mod-buildcraft.com/build_info_full/testing/BuildCraft/versions.txt") as bctRequest:
                    versionlistBCT = str(bctRequest.read())[2:].split(r"\n")
                    logging.info(f"found {len(versionlistBCT)} BuildCraft pre-releases")



        await asyncio.sleep(8)

from logging import INFO
logging.basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")

configuration.loadconfig()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop = asyncio.get_event_loop()
loop.run_until_complete(runVersionChecker())
loop.close()