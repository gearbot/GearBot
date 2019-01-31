from tornado.web import removeslash

from Other.PrimaryHandler import PrimaryHandler


class Root(PrimaryHandler):
    @removeslash
    async def get(self):
        self.write("Welcome to the Gearbot App info page")
        self.finish()