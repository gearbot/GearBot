from Other.Handlers import SocketNamespace

from Other import BackendUtils

class GuildPage(SocketNamespace):
    async def on_connect(self, sid, environ):
        pass

    async def on_disconnect(self, sid):
        pass
    
    async def on_get(self, sid, data):
        verified_status = await self.verify_client(data)

        guildPageData = {
            "name": "The Gearbox",
            "owner": "AEnterprise#4693",
            "id": 365498559174410241,
            "members": 127,
            "textChannels": 22,
            "voiceChannels": 1,
            "totalChannels": 23,
            "creationDate": "05-10-2017 (538 days ago)",
            "vipFeatures": False,
            "serverIcon": "https://cdn.discordapp.com/icons/365498559174410241/735df5f0db5581592b7744f8fc10701f.webp?size=1024",
            "roles": [
                "Gear Spinners",
                "Gear Creators",
                "Amazing Gears"
            ],
            "serverEmojiCount": 51,
            "memberStatuses": {
                "online": 11,
                "idle": 10,
                "dnd": 10,
                "offline": 96
            }
        }

        await self.emit("api_response",
            # Format is [uptime(s), commandCount, messageCount, guildCount, 
            # errorCount, totalUserCount, uniqueUserCount, tacoTime]
            data = guildPageData
        )
