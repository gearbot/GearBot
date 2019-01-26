from tornado.web import RequestHandler


class PrimaryHandler(RequestHandler):
    def get_current_user(self):
        userIDCookie = self.get_secure_cookie("userauthtoken")
        if userIDCookie != None:
            return userIDCookie.decode()
        else:
            return None