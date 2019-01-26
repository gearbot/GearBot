from tornado.web import removeslash

from web.backend.Other.PrimaryHandler import PrimaryHandler


class AuthGetTestingEndpoint(PrimaryHandler):
    @removeslash
    async def get(self):
        auth_id = self.get_secure_cookie("userauthtoken")
        if auth_id is not None:
            self.write(f"Auth cookie is: {auth_id.decode()}")
        else:
            self.write("Auth cookie is invalid, please try again!")
        self.finish()