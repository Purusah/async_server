import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.options
from uuid import uuid4
import pymongo
import motor.motor_tornado


tornado.options.define("port", default=8000, type=int)


class MainHandler(tornado.web.RequestHandler):
    _cookie_robin = "Robin8"

    def _set_cookies(self):
        cookie = str(uuid4())
        self.set_cookie(self._cookie_robin, cookie)
        return cookie

    def _have_cookies(self):
        cookie = self.cookies.get(self._cookie_robin)
        return cookie

    async def _check_name(self, cookie):
        query = {
            "cookie": str(cookie)
        }
        result = await self.application.db_coll.find_one(query)
        print("Result: ", result)
        if result:
            return result.get("name")
        else:
            return None

    async def check_name_cookies(self):
        cookie = self._have_cookies()
        if cookie == None:
            self._set_cookies()
            res = {
                "cookie": None,
                "name": None,
            }
        else:
            name = await self._check_name(cookie)
            res = {
                "cookie": cookie,
                "name": name,
            }
        return res


    async def get(self):
        res = await self.check_name_cookies()
        self.render("index.html", cookie=res.get("cookie"), name=res.get("name"))


class LoginHandler(MainHandler):
    async def get(self):
        res = await super().check_name_cookies()
        self.render("login.html", cookie=res.get("cookie"), name=res.get("name"))

    async def _set_name(self, name, cookie):
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

    async def post(self):
        name = self.get_body_argument("name")
        if bool(name):
            cookie = super()._have_cookies()
            await self._set_name(name, cookie)
            self.redirect("/")
            return
        else:
            self.redirect("/login")
            return


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