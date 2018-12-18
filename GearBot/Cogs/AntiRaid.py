import asyncio
import aioredis

import discord
from discord.ext import commands

from Util import GearbotLogging, Utils


class AntiRaid:
	def __init__(self, bot):
		GearbotLogging.info("AntiRaid watcher starting!")
		self.bot: commands.Bot = bot
		self.running = True
		self.bot.loop.create_task(raid_check(self)) # Watch for raids

	async def on_member_join(self, member: discord.Member):
		redisDB = await databaseConnection()
		userJoinKey = str(member.id)+"GID"+str(member.guild.id)

		redisDB.execute("set", userJoinKey + "_60s", "", "ex", 60)
		redisDB.execute("set", userJoinKey + "_30s", "", "ex", 30)	

	async def sound_the_alarm(self, guild, offendingUsers):
		print("Alarm triggered in guild " + guild)
		pass

def setup(bot):
	bot.add_cog(AntiRaid(bot))

async def raid_check(self):
	redisDB = await databaseConnection()
	oldScanRun = []
	while True:
		dbPointer = 0
		firstSearch = True
		shortListData = []
	
		while dbPointer != 0 or firstSearch == True:
			dbScanRaw = await redisDB.execute("scan", dbPointer, "match", "*_30s*", "count", 200000)
			shortListData += dbScanRaw[1]
			dbPointer = int(dbScanRaw[0])
			firstSearch = False

		if shortListData != oldScanRun: #or (now - tracker[-5].joined_at).seconds <= 30: # Assume count of 7 wanted
			shortListFormatted = []
			for user in shortListData: # Send it off to the banners
				shortListFormatted.append(user[:-4].split("GID")) # Remove the timing data. Format is [userID, guildID]

			for _, guildID in shortListFormatted:
				guildRaiders = []
				for userID, guildIDMatch in shortListFormatted:
					if guildID == guildIDMatch:
						guildRaiders.append(userID)

				if len(guildRaiders) >= 6: # That guild hit too many, sound the alarm!
					await self.sound_the_alarm(guild = guildID, offendingUsers = guildRaiders)
					break

		oldScanRun = shortListData[:-5]
		await asyncio.sleep(1)

async def databaseConnection():
	try:
		redisDB = await aioredis.create_connection(("localhost", 6379), encoding="utf-8")
		return redisDB
	except OSError:
		GearbotLogging.warn("Connection to redis could not be established, AntiRaid not starting!")
		return