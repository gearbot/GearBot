import asyncio
import math
import os
import re

import aiohttp
import discord
from PIL import Image

from Util import Translator, Emoji

EMOJI_LOCKS = []
JUMBO_NUM = 0
JUMBO_TARGET_SIZE = 128
JUMBO_PADDING = 6


class EmojiHandler:
    def __init__(self, extension, link, matcher=None, has_frames=False):
        self.extension = extension
        self.matcher = matcher
        self.link = link
        self.has_frames = has_frames

    def match(self, text):
        match = self.matcher.match(text)
        if match is None:
            return text, None
        return "".join([text[match.end(0):], match.group(1)]), match.group(2)

    async def fetch(self, eid, session: aiohttp.ClientSession):
        if eid not in EMOJI_LOCKS:
            async with session.get(self.link.format(eid=eid, extension=self.extension)) as r:
                if r.status is not 200:
                    return False
                with open(f"emoji/{eid}.{self.extension}", "wb") as file:
                    file.write(await r.read())
        EMOJI_LOCKS.append(eid)
        return True

    def get_image(self, eid, frame=None):
        image = Image.open(f"emoji/{eid}.{self.extension}")
        return image.resize((round(image.size[0] * (JUMBO_TARGET_SIZE / image.size[1])),
                      round(image.size[1] * (JUMBO_TARGET_SIZE / image.size[1]))))

    @staticmethod
    def get_frame_count(eid):
        return 0

    def cleanup(self, eid):
        EMOJI_LOCKS.remove(eid)
        file_name = f"emoji/{eid}.{self.extension}"
        if eid not in EMOJI_LOCKS and os.path.isfile(file_name):
            os.remove(file_name)


class TwermojiHandler(EmojiHandler):
    def __init__(self, count):
        super().__init__("png", 'https://twemoji.maxcdn.com/2/72x72/{eid}.{extension}')
        self.has_frames = False
        self.count = count

    def match(self, text):
        char = text[:self.count]
        return text[self.count:], '-'.join(char.encode("unicode_escape").decode("utf-8")[2:].lstrip("0") for char in char)


HANDLERS = [
    EmojiHandler("png", "https://cdn.discordapp.com/emojis/{eid}.{extension}", re.compile('([^<]*)<:(?:[^:]+):([0-9]+)>')),
    EmojiHandler("gif", "https://cdn.discordapp.com/emojis/{eid}.{extension}", re.compile('([^<]*)<a:(?:[^:]+):([0-9]+)>')),
    TwermojiHandler(4),
    TwermojiHandler(3),
    TwermojiHandler(2),
    TwermojiHandler(1),
]


class JumboGenerator:

    def __init__(self, ctx, text):
        global JUMBO_NUM
        JUMBO_NUM += 1
        self.ctx = ctx
        self.text = text
        self.e_list = []
        self.number = JUMBO_NUM

        if not os.path.isdir("emoji"):
            os.mkdir("emoji")

    async def generate(self):
        try:
            await asyncio.wait_for(self.prep(), timeout=20)
            await asyncio.wait_for(self.build(), timeout=60)
        except asyncio.TimeoutError:
            await self.ctx.send(f"{Emoji.get_chat_emoji('WHAT')} {Translator.translate('jumbo_timeout', self.ctx)}")
        else:
            if len(self.e_list) > 0:
                await self.send()
                self.cleanup()
            else:
                await self.ctx.send(f"{Emoji.get_chat_emoji('WRENCH')} {Translator.translate('jumbo_no_emoji', self.ctx)}")

    async def prep(self):
        prev = 0
        for part in self.text.split(" "):
            while 0 < len(part) != prev:
                prev = len(part)
                for handler in HANDLERS:
                    new_part, eid = handler.match(part)
                    if eid is not None and eid != "" and await handler.fetch(eid, self.ctx.bot.aiosession):
                        self.e_list.append((eid, handler))
                        part = new_part
                        prev = 0
                        break



    async def build(self):
        size = JUMBO_TARGET_SIZE + JUMBO_PADDING * 2

        emoji_count = len(self.e_list)
        if emoji_count > 8:
            square = math.sqrt(emoji_count)
            columns = int(square)
            rows = int(emoji_count / columns)
            if emoji_count > rows * columns:
                rows += 1
        else:
            columns = emoji_count
            rows = 1

        #todo: animated handling

        if emoji_count > 0:
            result = Image.new('RGBA', (size * columns, size * rows))

            count = 0
            for eid, handler in self.e_list:
                x = count % columns
                y = math.floor(count / columns)
                image = handler.get_image(eid)
                result.paste(image, (round((x * size) + (size / 2) - (image.size[0] / 2)), round(y * size + JUMBO_PADDING)))
                count += 1

            result.save(f"emoji/jumbo{self.number}.png")


    async def send(self):
        await self.ctx.send(file=discord.File(open(f"emoji/jumbo{self.number}.png", "rb"), filename="emoji.png"))


    def cleanup(self):
        for eid, handler in self.e_list:
            handler.cleanup(eid)
        os.remove(f"emoji/jumbo{self.number}.png")