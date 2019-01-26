from tornado.web import authenticated, removeslash

from web.backend.Other import BackendUtils
from web.backend.Other.PrimaryHandler import PrimaryHandler
from web.backend.Other.RedisMessager import Messager


class GearbotDashboard(PrimaryHandler):

    def initialize(self, messager=None):
        self.messager:Messager = messager


    @authenticated
    @removeslash
    async def get(self):
        userID = self.get_current_user()
        if userID is None:
            self.redirect("/discordlogin")
            return

        perm_data = await BackendUtils.get_guilds_perms(userID)
        print("This is the perm data!: " + str(perm_data))
        self.write("Done")
        self.finish()

