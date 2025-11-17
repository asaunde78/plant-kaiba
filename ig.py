import requests
from dotenv import load_dotenv
import json
import os 
import flask
load_dotenv()
class URLObject(): 
    def __init__(self, secret, base_url):
        self.base_url = base_url
        self.params = {"platform":"instagram", "access_token":secret}
        self.json = {}
    def get(self, url):
        self.json = requests.get(url=self.base_url + url, params=self.params)
        return self.json
    def post(self,url, data):
        self.json = requests.post(url=self.base_url + url, params=self.params, json=data)
        return self.json
    def print(self):
        print(json.dumps(self.json.json(), indent=4))
    


# print(os.getenv("APP-SECRET"))
secret = os.getenv("IG_ACCESS_TOKEN")
base = "https://graph.instagram.com/v23.0/"

igurl = URLObject(secret,base)


igurl.get("794018049617142/")
igurl.print()

# igurl.get("me/conversations?fields=messages{created_time,from,message,id,shares}&limit=1&offset=1")
# igurl.print()


# conversations = igurl.json.json()
# for msg in conversations["data"][0]["messages"]["data"]:
# # msg_id = conversations["data"][0]["messages"]["data"][0]["id"]
#     msg_id = msg["id"]
#     # print(msg_id)
#     r = igurl.get(msg_id + "?fields=messages{shares}")
#     print("Second call", json.dumps(r.json(), indent=4))
