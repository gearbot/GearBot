import asyncio
import datetime
import json

import aiohttp
import discord
from discord.ext import commands

from Util import GearbotLogging, Pages


class Minecraft:

    def __init__(self, bot):
        self.bot:commands.Bot = bot
        self.cf_cache = dict()
        self.fetching = []
        Pages.register("cf", self.init_cf, self.update_cf)


    async def get_info(self, ctx, project_name, log):
        while project_name in self.fetching:
            #already fetching, wait for data to arrive
            await asyncio.sleep(1)
        if not project_name in self.cf_cache.keys():
            self.fetching.append(project_name)
            if log:
                message = await ctx.send("<a:gearLoading:468054357724889089> Fetching info, please hold <a:gearLoading:468054357724889089>")
            info = await self.fetch_info(project_name)
            if info is False:
                if log:
                    await ctx.send("Data retrieval failed, seems like the API is having issues, please try again later.")
            else:
                GearbotLogging.info(f"Retrieved project data for {project_name}, adding to cache.")
                self.cf_cache[project_name] = {
                    "info": info,
                    "time": datetime.datetime.utcnow()
                }
            self.fetching.remove(project_name)
            if log:
                await message.delete()
            return info
        else:
            return self.cf_cache[project_name]["info"]


    async def fetch_info(self, project_name):
        session: aiohttp.ClientSession = self.bot.aiosession
        async with session.get(f"https://api.cfwidget.com/projects/{project_name}") as reply:
            if reply.status is 200: #all good, we can parse it
                parsed = json.loads(await reply.text())
                p_type = parsed["type"]
                info = {
                    "title": parsed["title"],
                    "type": f'{parsed["game"]} {p_type[:-1] if p_type.endswith("s") else p_type}',
                    "updated": parsed["last_fetch"],
                    "categories": parsed["categories"],
                    "links": dict(),
                    "thumbnail": parsed["thumbnail"],
                    "downloads": parsed["downloads"]["total"]
                }

                for link in parsed["links"]:
                    info["links"][link["title"]] = link["href"]

                #todo: files

                return info

            elif reply.status is 202: #new project, wait for the api to fetch it
                GearbotLogging.info(f"Info for {project_name} not available yet, trying again in 10 seconds.")
                await asyncio.sleep(10)
                return await self.fetch_info(project_name)
            elif reply.status in (400, 404):
                return None
            elif reply.status is 500:
                GearbotLogging.error(f"Fetching info for {project_name} failed.")
                return False
            else:
                GearbotLogging.error(f"Got unexpected response code ({reply.status}) when fetching info for {project_name}.")
                return None #TODO: handle failure

    async def gen_cf_pages(self, ctx, project_name, log):
        info = await self.get_info(ctx, project_name, log)
        if info is None:
            return None
        else:
            fields = {
                "Project name": info["title"],
                "Project type": info["type"].lower(),
                "Project categories": "\n".join(info["categories"]),
                "Links": "\n".join(f"[{k}]({v})" for k, v in info["links"].items()),
                "Downloads": "{:,}".format(info["downloads"])
            }
            return Pages.paginate_fields([fields])

    @commands.command()
    async def curse(self, ctx, project_name: str):
        await Pages.create_new("cf", ctx, project_name=project_name)

    async def init_cf(self, ctx, project_name):
        pages = await self.gen_cf_pages(ctx, project_name, True)
        if pages is None:
            return "Unable to fetch info for that project, are you sure it exists?", None, False
        embed = discord.Embed(title=f"Curseforge info for {project_name}")
        for k, v in pages[0].items():
            embed.add_field(name=k, value=v)
        return None, embed, len(pages) > 1

    async def update_cf(self, ctx, message, page_num, action, data):
        pages = await self.gen_cf_pages(ctx, data["project_name"], False)
        if pages is None:
            return "Unable to fetch info for that project, are you sure it exists?", None, False
        embed = discord.Embed(title=f"Curseforge info for {data['project_name']}")
        page, page_num = Pages.basic_pages(pages, page_num, action)
        for k, v in page.items():
            embed.add_field(name=k, value=v)
        return None, embed, page_num



def setup(bot):
    bot.add_cog(Minecraft(bot))