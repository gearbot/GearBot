from tornado import ioloop
from tornado import web
from tornado.httpserver import HTTPServer
from tornado.options import parse_command_line

from Other import BackendUtils
print("Registering HMAC key...")
loop = ioloop.IOLoop.current()
loop.asyncio_loop.run_until_complete(BackendUtils.crypto_initalize())

from Other.Handlers import SocketHandler
from Other.RedisMessager import Messager

from routes.discordauth.discordcallback import DiscordOAuthCallback
from routes.discordauth.discordlogin import DiscordOAuthRedir
from routes.testing.frontend import FrontendAPIGuildInfo
from routes.testing.setauth import AuthSetTestingEndpoint

print("Starting Gearbot Backend")

parse_command_line()
messager = Messager("bot-dash-messages", "dash-bot-messages", loop.asyncio_loop)
loop.asyncio_loop.create_task(BackendUtils.initialize(messager))

web_settings = {
    "cookie_secret": BackendUtils.HMAC_KEY,
    "login_url": "/discord/login",
    "xsrf_cookies": False # Turn on when not testing
}

dashboardAPI = web.Application([
    (r"/discord/login", DiscordOAuthRedir), #ihateredirectcaches, #me too
    (r"/discord/callback", DiscordOAuthCallback),
    (r"/setauth", AuthSetTestingEndpoint),
    (r"/testing", FrontendAPIGuildInfo),

    (r"/ws/", SocketHandler)
], **web_settings, debug=True)

dashboard_server = HTTPServer(dashboardAPI) # Create the Tornado server
dashboard_server.listen(8081)
loop.start()