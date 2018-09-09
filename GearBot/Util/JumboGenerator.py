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
JUMBO_PADDING = 4


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

class EmojiIterator:
    def __init__(self, emoji):
        self.emoji = emoji
        self.mode = "LINE"
        self.count = -1
        self.x = -1
        self.y = 0

        emoji_count = len(emoji)
        self.width = emoji_count
        self.height = 1

        if emoji_count >= 3:
            if emoji_count % 2 == 0:
                side = round(math.sqrt(emoji_count))
                if side * side == emoji_count:
                    self.mode = "RECTANGLE"
                    self.width = self.height = side
            elif emoji_count >= 8:
                left = emoji_count
                count = 0
                sum = 0
                while left > 0:
                    count += 1
                    left -= count
                    sum += count
                    if (sum - count) == left:
                        self.mode = "DIAMOND"
                        self.width = count
                        self.height = (count * 2) - 1
                        self.row_size = 1
                        break
                if left is 0 or (left is -1 and count % 2 == 0):
                    self.mode = "TRIANGLE"
                    self.width = self.height = count
                    self.row_size = 1

            if self.mode == "LINE" and emoji_count > 8:
                self.mode = "RECTANGLE"
                a = math.ceil(math.sqrt(emoji_count))
                while emoji_count % a != 0:
                    a -= 1
                b = int(emoji_count / a)
                self.width = max(a, b)
                self.height = min(a, b)

            if emoji_count > 8 and self.height is 1:
                self.mode = "CROSS"
                self.height = self.width = math.ceil(emoji_count / 2)



    @property
    def size(self):
        return self.width, self.height

    def __iter__(self):
        return self

    def __next__(self):
        if self.count + 1 >= len(self.emoji):
            raise StopIteration

        self.count += 1
        self.x += 1

        size = JUMBO_TARGET_SIZE + JUMBO_PADDING * 2
        eid, handler = self.emoji[self.count]
        image = handler.get_image(eid)
        image_offset = math.floor((size / 2) - (image.size[0] / 2))

        if self.mode == "LINE":
            return image, (self.x * size + image_offset, 0)
        elif self.mode == "RECTANGLE":
            self.limit_line(self.width)
            return image, (self.x * size + image_offset, self.y * size)
        elif self.mode == "TRIANGLE" or self.mode == "DIAMOND":
            if self.x >= self.row_size:
                self.row_size += (1 if self.count < len(self.emoji)/2 or self.mode == "TRIANGLE" else -1)
                self.next_line()
            row_offset = (self.width - self.row_size) * size / 2
            x_offset = math.floor(row_offset + (self.x * size))
            y_offset = self.y * size
            return image, (x_offset + image_offset, y_offset)
        elif self.mode == "CROSS":
            line_limit = self.width if (math.floor(self.height/2)-1 == self.y) else 1
            self.limit_line(line_limit)
            modifier = 0 if math.floor(self.height/2)-1 == self.y else self.width / 2
            x_offset = math.floor((self.x + modifier - 1) * size)
            y_offset = math.floor(self.y * size)
            return image, (x_offset + image_offset, y_offset)

    def limit_line(self, limit):
        if self.x >= limit:
            self.next_line()

    def next_line(self):
        self.x = 0
        self.y += 1



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
        #todo: animated handling
        if len(self.e_list) > 0:
            iterator = EmojiIterator(self.e_list)
            size = JUMBO_TARGET_SIZE + JUMBO_PADDING * 2
            result = Image.new('RGBA', (size * iterator.width, size * iterator.height))
            print(iterator.mode)
            for info in iterator:
                result.paste(*info)
            result.save(f"emoji/jumbo{self.number}.png")


    async def send(self):
        await self.ctx.send(file=discord.File(open(f"emoji/jumbo{self.number}.png", "rb"), filename="emoji.png"))


    def cleanup(self):
        for eid, handler in self.e_list:
            handler.cleanup(eid)
        os.remove(f"emoji/jumbo{self.number}.png")