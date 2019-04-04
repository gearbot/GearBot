from Other.Handlers import SocketNamespace

from Other import BackendUtils

class GuildPage(SocketNamespace):
    async def on_connect(self, sid, environ):
        pass

    async def on_disconnect(self, sid):
        pass
    
    async def on_get(self, sid, data):
        client_id = data["client_id"]

        verified_status = await self.verify_client(data)
        if verified_status != 403:
            if verified_status == False:
                await self.emit("api_response", data = {"status": 400} )
                return
        else:
            await self.emit("api_response", data = {"status": 403} )
            return

        await self.add_known_socket(client_id, sid)

        guildPageData = {
            "name": "The Gearbox",
            "owner": "AEnterprise#4693",
            "id": 365498559174410241,
            "memberCount": 127,
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
            "serverEmoteCount": 51,
            "memberStatuses": {
                "online": 11,
                "idle": 10,
                "dnd": 10,
                "offline": 96
            }
        }
        await self.get_client_info(data)
        # Security logic here. Can use above function for comparisons
        await self.emit("api_response",
            data = guildPageData
        )
