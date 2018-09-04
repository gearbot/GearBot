import math
import os
import re

import aiohttp
import discord
from PIL import Image

CDN_URL = 'https://twemoji.maxcdn.com/2/72x72/{}.png'
EMOJI_LOCKS = []
JUMBO_NUM = 0
JUMBO_TARGET_SIZE = 128
JUMBO_PADDING = 6


class EmojiHandler:
    def __init__(self, extension, matcher, link, has_frames=False):
        self.extension = extension
        self.matcher = re.compile(matcher)
        self.link = link
        self.has_frames = has_frames

    def match(self, text):
        match = self.matcher.match(text)
        if match is None:
            return text, None
        return text[match.end(0):], match.group(1)

    async def fetch(self, eid, session: aiohttp.ClientSession):
        if eid not in EMOJI_LOCKS:
            async with session.get(self.link.format(eid=eid, extension=self.extension)) as r:
                with open(f"emoji/{eid}.{self.extension}", "wb") as file:
                    file.write(await r.read())
        EMOJI_LOCKS.append(eid)

    def get_image(self, eid, frame=None):
        image = Image.open(f"emoji/{eid}.{self.extension}")
        image.resize((round(image.size[0] * JUMBO_TARGET_SIZE / image.size[1]),
                      round(image.size[1] * JUMBO_TARGET_SIZE / image.size[1])))
        return image

    @staticmethod
    def get_frame_count(eid):
        return 0

    def cleanup(self, eid):
        EMOJI_LOCKS.remove(eid)
        file_name = f"emoji/{eid}.{self.extension}"
        if eid not in EMOJI_LOCKS and os.path.isfile(file_name):
            os.remove(file_name)


HANDLERS = [
    EmojiHandler("png", '(?:[^<]*)<:(?:[^:]+):([0-9]+)>', "https://cdn.discordapp.com/emojis/{eid}.{extension}"),
    EmojiHandler("gif", '(?:[^<]*)<a:(?:[^:]+):([0-9]+)>', "https://cdn.discordapp.com/emojis/{eid}.{extension}"),
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
        self.build_list()
        await self.fetch_all()
        self.build()
        await self.send()
        self.cleanup()

    def build_list(self):
        while len(self.text) > 0:
            for handler in HANDLERS:
                self.text, eid = handler.match(self.text)
                if eid is not None:
                    self.e_list.append((eid, handler))
                    break
            else:
                break

    async def fetch_all(self):
        for eid, handler in self.e_list:
            await handler.fetch(eid, self.ctx.bot.aiosession)

    def build(self):
        size = JUMBO_TARGET_SIZE + JUMBO_PADDING * 2

        emoji_count = len(self.e_list)
        square = math.sqrt(emoji_count)
        columns = int(square)
        rows = int(emoji_count / columns)
        if emoji_count > rows * columns:
            rows += 1

        #todo: animated handling

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