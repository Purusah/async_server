import tornado.ioloop
import tornado.web
import tornado.httpserver
import tornado.options
from uuid import uuid4
import time
import hashlib
import motor.motor_tornado
from jsonrpcclient.tornado_client import TornadoClient


tornado.options.define("port", default=8000, type=int)
tornado.options.define("hour_seconds", default=3600, type=int)
SEED = "seed"



class MainHandler(tornado.web.RequestHandler):
    _cookie_robin = "Robin8"
    _cur_time = time.time

    client = TornadoClient("http://localhost:8001/")

    async def _get_user_info(self):
        cookies = self._have_cookies()
        if bool(cookies):
            user_name = await self._check_name(cookies)
            balance = await self._check_balance(user_name)
        else:
            self._set_cookies()
            user_name = None
            balance = None
        return cookies, user_name, balance

    async def get(self):
        cookies, user_name, _ = await self._get_user_info()
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
        if result:
            return result.get("login")
        else:
            return None

    async def _check_balance(self, login):
        query = {
            "login": login
        }
        result = await self.application.db_coll.find_one(query)
        if result:
            return result.get("balance")
        else:
            return None


class SighUpHandler(MainHandler):

    async def get(self):
        cookies, user_name, _ = await super()._get_user_info()
        self.render("sign_up.html", cookie=cookies, name=user_name)

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
        if not await super()._check_name(cookie):
            query = {
                "login": login,
                "password": hashlib.md5(bytes("{}{}".format(password, SEED).encode())).hexdigest(),
                "cookie": str(cookie),
                "balance": 0,
            }
            await self.application.db_coll.insert_one(query)
        # else:
        #     await self.application.db_coll.update_one(
        #         {"cookie": str(cookie)},
        #         {
        #             "$set": {"name": name}
        #         }
        #     )

class SignInHandler(MainHandler):
    async def get(self):
        cookies, login, balance = await super()._get_user_info()
        if bool(login):
            self.redirect("/my_page")
            return
        self.render("sign_in.html", name=login, balance=balance)


class MyPageHandler(MainHandler):
    async def get(self):
        cookies, login, balance = await super()._get_user_info()
        if bool(login):
            self.redirect("/login")
            return
        self.render("my_page.html", name=login, balance=balance)

    async def post(self):
        amount = self.get_body_argument("amount")
        print("Amount: ", type(amount))
        params = {
            "amount": int(amount)
        }
        response = await super().client.request("update_balance", params)
        _, login, _ = await super()._get_user_info()
        await self.update_balance(login, amount)

    async def update_balance(self, login, amount):
        query = {
            "login": login
        }
        user_info = await self.application.db_coll.find_one(query)
        current_balance = user_info["balance"]
        await self.application.db_coll.update_one(
            {
                "login": login
            },
            {
                "$set": {"balance": amount + current_balance}
            }
        )
        self.make_bet(7, amount)
        self.redirect("/my_page")

    # async def make_bet(self, number, amount):
    #     params = {
    #         "number": number,
    #         "amount": amount,
    #     }
    #     response = await ().client.request("make_bet", params)
    #     self.write(response)


def make_app():
    app = Application()
    server = tornado.httpserver.HTTPServer(app)
    server.listen(8000)
    return app


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/login", SighUpHandler),
            (r"/my_page", MyPageHandler),
            (r"/sign_in", SignInHandler),
        ]
        client = motor.motor_tornado.MotorClient("localhost", 27017)
        self.db = client["users"]
        self.db_coll = self.db["names"]
        tornado.web.Application.__init__(self, handlers)


if __name__ == "__main__":
    app = make_app()
    tornado.ioloop.IOLoop.instance().start()
