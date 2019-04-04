from Other.Handlers import SocketNamespace

from Other import BackendUtils


class Guilds(SocketNamespace):
    async def on_connect(self, sid, environ):
        pass

    async def on_disconnect(self, sid):
        pass

    async def on_get(self, sid, data):
        # Temporary until guilds work
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
        # Security logic goes here

        await self.emit("api_response", 
            data = {
                "365498559174410241": {
                    "name": "The Gearbox",
                    "icon": "https://cdn.discordapp.com/icons/365498559174410241/735df5f0db5581592b7744f8fc10701f.webp",
                    "authorized": verified_status
                },
                # Current question: 1. Send a object for a guild that the user has no permissions in
                # 2. Send just "authorized": "false",
                # 3. Send nothing at all and handle client side not rendering it
                "029349238409030492232": { 
                    "name": "Gearbot Brain Server",
                    "icon": "https://cdn.discordapp.com/icons/365498559174410241/735df5f0db5581592b7744f8fc10701f.webp",
                    "authorized": False
                }
            }
        )
        
        """
        #todo: don't redirect but have the client open a popup
        userID = self.get_current_user()
        if userID is None:
            self.redirect("/discord/login")
        else:
            info = await BackendUtils.get_guilds_info(userID)
            self.finish(info)
        """
