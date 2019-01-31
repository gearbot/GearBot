from tornado.web import authenticated, removeslash

from Other import BackendUtils
from Other.PrimaryHandler import PrimaryHandler


class Guilds(PrimaryHandler):
    
    """
    # This is gonna need a fair bit of work to get going as intended
    @removeslash
    async def get(self):
        self.write({"I Despise": "CORS"})
        self.finish()

    """
    @authenticated
    @removeslash
    async def get(self):
        userID = self.get_current_user()
        if userID is None:
            self.redirect("/discord/login") # We may not need this?
        else:
            info = await BackendUtils.get_guilds_info(userID)
            self.finish(info)
