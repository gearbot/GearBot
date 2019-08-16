import asyncio
import datetime
import ujson
from collections import OrderedDict

import aiohttp
import discord

from Cogs.BaseCog import BaseCog
from Util import GearbotLogging, Pages, VersionInfo, Translator


class Minecraft(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)

        self.cf_cache = dict()
        self.fetching = []
        self.running = True
        self.bot.loop.create_task(expire_cache(self))

    def cog_unload(self):
        self.running = False

    async def get_info(self, ctx, project_name, log):
        while project_name in self.fetching:
            # already fetching, wait for data to arrive
            await asyncio.sleep(1)
        if not project_name in self.cf_cache.keys():
            self.fetching.append(project_name)
            if log:
                message = await ctx.send(
                    f"<a:gearLoading:468054357724889089> {Translator.translate('fetching_info', ctx)} <a:gearLoading:468054357724889089>")
            info = await self.fetch_info(project_name)
            if info is False:
                if log:
                    await ctx.send(Translator.translate('cf_fetch_failed', ctx))
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
        async with session.get(f"https://api.cfwidget.com/mc-mods/minecraft/{project_name}") as reply:
            if reply.status is 200:  # all good, we can parse it
                parsed = ujson.loads(await reply.text())
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

                mc_versions = []
                for k, v in parsed["versions"].items():
                    if "Java" not in k:
                        mc_versions.append(k)
                sorted = VersionInfo.getSortedVersions(mc_versions)
                map = OrderedDict()
                for version in sorted:
                    mod_versions_unsorted = dict()
                    mod_versions = OrderedDict()
                    version_list = []
                    for v2 in parsed["versions"][version]:
                        mod_versions_unsorted[v2["id"]] = v2
                        version_list.append(v2["id"])

                    version_list.sort()
                    version_list.reverse()
                    for v3 in version_list:
                        mod_versions[v3] = mod_versions_unsorted[v3]

                    map[version] = mod_versions
                info["versions"] = map
                return info

            elif reply.status is 202:  # New project, wait for the api to fetch it
                GearbotLogging.info(f"Info for {project_name} not available yet, trying again in 10 seconds.")
                await asyncio.sleep(10)
                return await self.fetch_info(project_name)
            elif reply.status in (400, 404):
                return None
            elif reply.status is 500:
                GearbotLogging.error(f"Fetching info for {project_name} failed.")
                return False
            else:
                GearbotLogging.error(
                    f"Got unexpected response code ({reply.status}) when fetching info for {project_name}.")
                return None  # TODO: handle failure

    async def gen_cf_pages(self, ctx, project_name, log):
        info = await self.get_info(ctx, project_name, log)
        if info is None:
            return None
        else:
            latest_mc = list(info["versions"].values())[0]
            latest_v = list(latest_mc.values())[0]
            latest = Translator.translate('cf_latest', ctx, name=latest_v['name'], version=latest_v['version'],
                                          downloads='{:,}'.format(latest_v['downloads']))
            fields = {
                Translator.translate('project_name', ctx): info["title"],
                Translator.translate('downloads', ctx): "{:,}".format(info["downloads"]),
                Translator.translate('latest', ctx): latest,
                Translator.translate('project_categories', ctx): "\n".join(info["categories"]),
                Translator.translate('links', ctx): "\n".join(f"[{k}]({v})" for k, v in info["links"].items())
            }
            return Pages.paginate_fields([fields])

    async def cf(self, ctx):
        """cf_help"""
        pass

    async def info(self, ctx, project_name: str):
        await Pages.create_new("cf", ctx, project_name=project_name)

    # @cf.command()
    # async def latest(self, ctx, project_name: str, version: str):
    #     await Pages.create_new("cf", ctx, project_name=project_name, version=version)

    async def init_cf(self, ctx, project_name):
        info = await self.get_info(ctx, project_name, True)
        pages = await self.gen_cf_pages(ctx, project_name, True)
        if pages is None:
            return Translator.translate('cf_not_found', ctx), None, False, []
        embed = discord.Embed(title=Translator.translate('cf_info_title', ctx, project_name=project_name))
        embed.set_thumbnail(url=info["thumbnail"])
        for k, v in pages[0].items():
            embed.add_field(name=k, value=v)
        return None, embed, len(pages) > 1, []

    async def update_cf(self, ctx, message, page_num, action, data):
        pages = await self.gen_cf_pages(ctx, data["project_name"], False)
        if pages is None:
            return Translator.translate('cf_not_found', ctx), None, False
        embed = discord.Embed(title=Translator.translate('cf_info_title', ctx, project_name=data['project_name']))
        page, page_num = Pages.basic_pages(pages, page_num, action)
        for k, v in page.items():
            embed.add_field(name=k, value=v)
        return None, embed, page_num


def setup(bot):
    bot.add_cog(Minecraft(bot))


async def expire_cache(self):
    GearbotLogging.info("Started CurseForge cache cleaning task")
    while self.running:
        if self.cf_cache != {}:
            for cachedproject, projectinfo in self.cf_cache.items():
                cachedtime = projectinfo["time"].minute
                currenttime = datetime.datetime.utcnow().minute
                if abs(cachedtime - currenttime) >= 10:
                    self.cf_cache.pop(cachedproject)  # Purging that projects cache
                    break
                else:
                    pass  # Its less then 10 minutes old, not touching
        else:
            pass  # We have nothing to purge

        await asyncio.sleep(5)
    GearbotLogging.info("CurseForge cache cleaning task terminated")
