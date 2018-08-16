import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.options
from uuid import uuid4
import time
import pymongo
import motor.motor_tornado


tornado.options.define("port", default=8000, type=int)
tornado.options.define("hour_seconds", default=3600, type=int)


class MainHandler(tornado.web.RequestHandler):
    _cookie_robin = "Robin8"
    _cur_time = time.time

    async def _get_user_info(self):
        cookies = self._have_cookies()
        if bool(cookies):
            user_name = await self._check_name(cookies)
        else:
            self._set_cookies()
            user_name = None
        return cookies, user_name

    async def get(self):
        cookies, user_name = await self._get_user_info()
        self.render("index.html", cookie=cookies, name=user_name)

    def _have_cookies(self):
        cookies = self.get_cookie(self._cookie_robin, default=None)
        if not cookies:
            return None
        else:
            return cookies

    def _set_cookies(self):
        name = self._cookie_robin
        value = str(uuid4())
        expires = self._cur_time() + tornado.options.options.hour_seconds
        # TODO: remove cookies from DB if expired
        self.set_cookie(name, value, expires=expires)

    async def _check_name(self, cookie):
        query = {
            "cookie": cookie
        }
        result = await self.application.db_coll.find_one(query)
        print("Result: ", result)
        if result:
            return result.get("name")
        else:
            return None


class LoginHandler(MainHandler):

    async def get(self):
        cookies, user_name = await super()._get_user_info()
        self.render("login.html", cookie=cookies, name=user_name)

    async def post(self):
        user_login = self.get_body_argument("login")
        user_password = self.get_body_argument("password")
        if bool(user_login) and bool(user_password):
            cookie = super()._have_cookies()
            # TODO add validation for unique user_login
            await self._set_credentials(user_login, user_password, cookie)
            self.redirect("/")
            return
        else:
            self.redirect("/login")
            return

    async def _set_credentials(self, login, password, cookie):
        if not super()._check_name(cookie):
            query = {
            "name": name,
            "cookie": str(cookie),
            }
            await self.application.db_coll.insert_one(query) #################
        else:
            await self.application.db_coll.update_one(
                {"cookie": str(cookie)},
                {
                    "$set": {"name": name}
                }
            )



class ErrorHandler(MainHandler):
    def get(self):
        super().get()


def make_app():
    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(8000)
    return app


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/login", LoginHandler),
            (r"/*", ErrorHandler),
        ]
        client = motor.motor_tornado.MotorClient("localhost", 27017)
        self.db = client["users"]
        self.db_coll = self.db["names"]
        tornado.web.Application.__init__(self, handlers)


if __name__ == "__main__":
    app = make_app()
    tornado.ioloop.IOLoop.instance().start()
