from tornado import ioloop
from tornado import web
from tornado.httpserver import HTTPServer
from tornado.options import parse_command_line

from Other import BackendUtils
from Other.RedisMessager import Messager
from routes.api.guids import Guilds
from routes.discordcallback import DiscordOAuthCallback
from routes.root import Root
from routes.temp.checkauth import AuthGetTestingEndpoint
from routes.temp.discordlogin import DiscordOAuthRedir
from routes.temp.frontend import FrontendAPIGuildInfo
from routes.temp.setauth import AuthSetTestingEndpoint

web_settings = {
    "cookie_secret": "4gjw63g34th3", #token_urlsafe(32),
    "login_url": "/discord/discordlogin",
    "xsrf_cookies": False # Turn on when not testing
}



print("Starting Gearbot App")


parse_command_line()
loop = ioloop.IOLoop.current()


messager = Messager("bot-dash-messages", "dash-bot-messages", loop.asyncio_loop)

loop.asyncio_loop.create_task(BackendUtils.initialize(messager))
dashboardAPI = web.Application([
    (r"/", Root),
    (r"/discord/discordlogin", DiscordOAuthRedir), #ihateredirectcaches
    (r"/discord/callback", DiscordOAuthCallback),
    (r"/setauth", AuthSetTestingEndpoint),
    (r"/checkauth", AuthGetTestingEndpoint),
    (r"/testing", FrontendAPIGuildInfo),

    (r"/api/guilds", Guilds),
], **web_settings, debug=True)
dashboard_server = HTTPServer(dashboardAPI) # Create the Tornado server
dashboard_server.listen(8081)
loop.start()