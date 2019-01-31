from tornado.web import removeslash

from Other import BackendUtils
from Other.PrimaryHandler import PrimaryHandler


class Guilds(PrimaryHandler):

    @removeslash
    async def get(self):
        #todo: don't redirect but have the client open a popup
        userID = self.get_current_user()
        if userID is None:
            self.redirect("/discord/login")
        else:
            info = await BackendUtils.get_guilds_info(userID)
            self.finish(info)
