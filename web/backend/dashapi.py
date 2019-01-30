from tornado import ioloop
from tornado import web
from tornado.httpserver import HTTPServer
from tornado.options import parse_command_line

from web.backend.Other import BackendUtils
from web.backend.Other.RedisMessager import Messager
from web.backend.routes.api.guids import Guilds
from web.backend.routes.discordcallback import DiscordOAuthCallback
from web.backend.routes.root import Root
from web.backend.routes.temp.checkauth import AuthGetTestingEndpoint
from web.backend.routes.temp.discordlogin import DiscordOAuthRedir
from web.backend.routes.temp.frontend import FrontendAPIGuildInfo
from web.backend.routes.temp.setauth import AuthSetTestingEndpoint

web_settings = {
    "cookie_secret": "4gjw63g34th3", #token_urlsafe(32),
    "login_url": "/discordlogin",
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
dashboard_server.listen(5000)
loop.start()