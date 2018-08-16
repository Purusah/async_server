import unittest
import requests
from bs4 import BeautifulSoup


class Client(object):
    @staticmethod
    def get(site=None):
        if site == None:
            response = requests.get("http://localhost:8000/", cookies="")
        else:
            response = requests.get("http://localhost:8000/", cookies="")
        return response


class MyTestCase(unittest.TestCase):
    def test_first_request(self):
        #c = Client()
        response = BeautifulSoup(Client.get().raw, "lxml")
        t = response.find("p", {"id":"no_cookie"})
        if not t:
            assert(t == "You have no cookies")




if __name__ == '__main__':
    unittest.main()
