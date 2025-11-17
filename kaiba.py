import requests
from dotenv import load_dotenv
import json
import os 
import urllib.request
from urllib.parse import urlparse, parse_qs
import ffmpeg

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
secret = os.getenv("IG_ACCESS_TOKEN")
base = "https://graph.instagram.com/v23.0/"
igurl = URLObject(secret,base)
        
from minio.commonconfig import Tags 
from minio import Minio 


min_cli = Minio("s3.vaughn.sh", os.getenv("S3_ACCESS"), os.getenv("S3_SECRET"))

print(min_cli.list_buckets())
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

@app.route("/instagram", methods=["GET","POST"])
def insta():
    if(request.method=="POST"):
        # print(json.dumps(request.get_json(), indent=4))
        body = {"content":"test"}
        entry = request.get_json().get("entry")
        
        if (entry and entry[0]) :
            mes = entry[0].get("messaging")
            print(json.dumps(mes, indent=4))
            if(mes and mes[0]):
                message = mes[0].get("message")
                if (message):
                    attach = message.get("attachments")
                    if(attach and attach[0]):
                        payload = attach[0].get("payload")
                        if(payload):
                            print("[WORKING] hello???")
                            
                            url = payload.get("url")
                            title =  payload.get("title")
        

                            stream = min_cli.list_objects("zink", "kaiba", True)
                            print(stream)
                            part_size = 10 * 1024 * 1024
                            with urllib.request.urlopen(url) as response:
                                tags = Tags(for_object=True)
                                user_id = mes[0].get("sender").get("id")
                                tags["User"] = user_id
                                user_data = igurl.get(user_id).json()
                                print(user_data)
                                tags["Timestamp"] = str(mes[0].get("timestamp")) 
                                # print(response.headers)
                                content_type = response.headers.get_content_type().split("/")[-1]
                                u = urlparse(url)
                                q = parse_qs(u.query)
                                f_name = "temp"
                                if("asset_id" in q):
                                    f_name = q["asset_id"][0]
                                # print("file name:",f_name)
                                data = response
                                min_cli.put_object("zink", f"kaiba/{f_name}.{content_type}", data, length=-1, part_size=part_size, tags=tags)
                                body = {"content": f"Sent by: {user_data.get("username")} \n [{title if title else "no title"}]({url})"}
                                res = requests.post(os.getenv("WEBHOOK"), json = body)
        return Response(status=200, mimetype='application/json')
    if(request.method=="GET"):
        print(request.args)
        if request.args["hub.mode"] == 'subscribe' and request.args["hub.verify_token"] == os.getenv("TOKEN"):
            return request.args["hub.challenge"]
        return Response(status=400, mimetype='application/json')
    return Response(status=400, mimetype='application/json')
        

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=8887)