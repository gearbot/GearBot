import asyncio
import logging
from multiprocessing import Process
from queue import Queue

import discord

p = None
queue:Queue = Queue()


def start_timer(client):
    global p
    p = Process(target=internalTimer, args=(queue,client,))
    p.start()
    queue.put(testing)

async def testing(client:discord.Client):
    logging.info("this works!")

def stop_timer():
    global p
    p.terminate()


def internalTimer(queue:Queue, client:discord.Client):
    loop = asyncio.get_event_loop()
    while True:
        while not queue.empty():
            loop.run_until_complete(execTimer(queue.get(), client))
            loop.run_until_complete(asyncio.sleep(5))


async def execTimer(fun, client):
    await fun(client)
    # from Variables import MINECRAFT_TERMINATED, MINECRAFT_RUNNING
    # global MINECRAFT_TERMINATED, MINECRAFT_RUNNING
    # # print(f"timer trigger, {MINECRAFT_RUNNING}, {MINECRAFT_TERMINATED}")
    # if MINECRAFT_RUNNING and MINECRAFT_TERMINATED:
    #     MINECRAFT_TERMINATED = MINECRAFT_RUNNING = False
    #     await GearbotLogging.logToLogChannel("Minecraft terminated")