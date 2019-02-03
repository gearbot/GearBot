from Other.Handlers import SocketNamespace

from Other import BackendUtils


class Guilds(SocketNamespace):
    async def on_connect(self, sid, environ):
        pass

    async def on_disconnect(self, sid):
        pass

    async def on_get(self, sid, data):
        # Temporary until guilds work
        verified = await self.verify_client(data)
        await self.emit("api_response", 
            data = verified
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
