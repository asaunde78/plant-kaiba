import requests
from dotenv import load_dotenv
import json
import os 
import urllib.request
from urllib.parse import urlparse, parse_qs
import ffmpeg
import discord 
import json 
from datetime import datetime, tzinfo
from pytz import timezone 
import io 

import aiohttp
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

webhook = discord.SyncWebhook.from_url(os.getenv("WEBHOOK"))


app = Flask(__name__)

@app.route("/instagram", methods=["GET","POST"])
def insta():
    if(request.method=="POST"):
        # print(json.dumps(request.get_json(), indent=4))
        body = {"content":"test"}
        entry = request.get_json().get("entry")
        
        if (not entry or  not entry[0]) :
            return Response(status=500, mimetype='application/json')
        mes = entry[0].get("messaging")
        print(json.dumps(mes, indent=4))
        if(not mes or not mes[0]):
            return Response(status=500, mimetype='application/json')
        message = mes[0].get("message")
        if (not message):
            return Response(status=500, mimetype='application/json')
        attach = message.get("attachments")
        if(not attach or not attach[0]):
            return Response(status=500, mimetype='application/json')
        payload = attach[0].get("payload")
        if(not payload):
            return Response(status=500, mimetype='application/json')
            
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
            arr = io.BytesIO()
            copy = io.BytesIO()
            while True:
                # Read a chunk of data from the response
                chunk = data.read(200)
                # print(chunk)
                if not chunk:
                    # Break the loop if no more data is received
                    break
                # Write the chunk to the BytesIO buffer
                arr.write(chunk)
                copy.write(chunk)
        
            arr.seek(0)
            copy.seek(0)
            f = discord.File(arr, filename=f"temp.{content_type}")
            min_cli.put_object("zink", f"kaiba/{f_name}.{content_type}", copy, length=-1, part_size=part_size, tags=tags)
            body = {"content": f"Sent by: {user_data.get("username")} \n [{title if title else "no title"}]({url})"}
            
        
            
            embed = discord.Embed( description= title if title else "no title", timestamp=datetime.fromtimestamp(int(mes[0].get("timestamp"))/1000, tz=timezone("US/Eastern")))
            embed.set_author(name=user_data.get("username"),icon_url=user_data.get("profile_pic"))
            
            
            print(response.status, response.url, response.headers)
            
            webhook.send(file=f, embed=embed)
            body = {"content":f"[content]({url})", "embeds":[embed.to_dict()]}
            # print("E TO D", body)
            # res = requests.post(os.getenv("WEBHOOK"), json = body)
            # res = requests.post(os.getenv("WEBHOOK"), json = body, headers={"Content-Type":"application/json"})
            # print(res, res.reason, res.text)
        return Response(status=200, mimetype='application/json')
    if(request.method=="GET"):
        print(request.args)
        if request.args["hub.mode"] == 'subscribe' and request.args["hub.verify_token"] == os.getenv("TOKEN"):
            return request.args["hub.challenge"]
        return Response(status=400, mimetype='application/json')
    return Response(status=400, mimetype='application/json')
        

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=8887)