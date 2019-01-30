from tornado.web import authenticated, removeslash

from web.backend.Other import BackendUtils
from web.backend.Other.PrimaryHandler import PrimaryHandler


class Guilds(PrimaryHandler):


    @authenticated
    @removeslash
    async def get(self):
        userID = self.get_current_user()
        if userID is None:
            self.redirect("/discordlogin")
        else:
            info = await BackendUtils.get_guilds_info(userID)
            self.finish(info)

