import logging
import sys

logger = logging.getLogger('gearbot')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='gearbot.log', encoding='utf-8', mode='w+')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler(stream=sys.stdout))

def info(message):
    logger.info(message)