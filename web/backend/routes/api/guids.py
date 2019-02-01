from socketio import AsyncNamespace

from Other import BackendUtils

class Guilds(AsyncNamespace):
    async def on_connect(self, sid, environ):
        pass

    async def on_disconnect(self, sid):
        pass

    async def on_get(self, sid, data):
        # Temporary until guilds work
        await self.emit("api_response", 
            data = []
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
