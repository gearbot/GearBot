from tornado.web import RequestHandler


class PrimaryHandler(RequestHandler):
    def get_current_user(self):
        userIDCookie = self.get_secure_cookie("userauthtoken")
        if userIDCookie is not None:
            return userIDCookie.decode()
        else:
            return None

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')