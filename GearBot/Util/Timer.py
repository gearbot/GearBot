import asyncio

from Util import GearbotLogging

p = None


def start_timer():
    global p
    from multiprocessing import Process
    p = Process(target=internalTimer)
    p.start()


def stop_timer():
    global p
    p.terminate()


def internalTimer():
    loop = asyncio.get_event_loop()
    while True:
        loop.run_until_complete(execTimer())
        loop.run_until_complete(asyncio.sleep(5))


async def execTimer():
    from Variables import MINECRAFT_TERMINATED, MINECRAFT_RUNNING
    global MINECRAFT_TERMINATED, MINECRAFT_RUNNING
    print(f"timer trigger, {MINECRAFT_RUNNING}, {MINECRAFT_TERMINATED}")
    if MINECRAFT_RUNNING and MINECRAFT_TERMINATED:
        MINECRAFT_TERMINATED = MINECRAFT_RUNNING = False
        await GearbotLogging.logToLogChannel("Minecraft terminated")