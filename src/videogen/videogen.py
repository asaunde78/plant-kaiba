from datetime import datetime, tzinfo
from pytz import timezone 
import time 

import json 
import requests
from upload_video import *

from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips, ImageClip
from moviepy.video.fx import *
import ffmpeg


from minio.commonconfig import Tags 
from minio import Minio 
import os
from argparse import Namespace
import random

from dotenv import load_dotenv
load_dotenv()

min_cli = Minio("s3.vaughn.sh", os.getenv("S3_ACCESS"), os.getenv("S3_SECRET"))


def get_seconds(s):
    if(s < 10):
        return "0" + str(s)
    return str(s)


def convert_second(s):
    if(s < 60):
        return "00:" + get_seconds(s)
    else:
        return get_seconds(s // 60) + ":" + get_seconds(s % 60)




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


# print(min_cli.list_buckets())
def get_all_videos():
    videos = list(min_cli.list_objects("zink", prefix="kaiba", recursive=True))
    # random.shuffle(videos)
    videos.sort( key = lambda vid:  -int(min_cli.get_object_tags("zink", vid.object_name)["Timestamp"]))
    # datetime.fromtimestamp(int(tags["Timestamp"])/1000, tz=timezone("US/Eastern"))
    
    return videos

def single_video(file_name, obj_name, tags):

    filename = "videos/" + str(file_name) + ".mp4" 
    min_cli.fget_object("zink", obj_name, filename)
    
    
    user_data = igurl.get(tags["User"]).json()
    
    print(user_data.get("username"), obj_name)

    pfp_file_path = "images/" + str(tags["User"]) + ".png"
    if (not  os.path.isfile(pfp_file_path)):
        r = requests.get(user_data.get("profile_pic"), stream=True)
        if r.status_code == 200:
            with open(pfp_file_path, "wb") as f:
                for chunk in r:
                    f.write(chunk)
                    
    post_time = datetime.fromtimestamp(int(tags["Timestamp"])/1000, tz=timezone("US/Eastern"))
    time_string = post_time.strftime("%m/%d/%Y, %I:%M:%S %p") #+ (" PM" if post_time.hour >= 12 else " AM")
    left_text = f"{time_string} \n {user_data.get("name") if user_data.get("name") else user_data.get("username") } \n (@{user_data.get("username")})"
    
    
    video = VideoFileClip(filename)

    padding = 400
    video = video.with_effects(
        [Resize(width=1040),
        Margin( left=padding, right=padding),
    ])

        
    
    user_text = TextClip(text = left_text, size=(padding-10,300), method="caption", color="white", font_size = 30, duration = video.duration).with_position(("left", "center")) 
    pfp_size = 100
    pfp = ImageClip(pfp_file_path, duration=video.duration).with_position((200 - pfp_size/2, (video.h /2 - user_text.h/2 - pfp_size/2))).resized((pfp_size,pfp_size))
    output = CompositeVideoClip([video, user_text, pfp])
    output.with_effects(
        [Resize(width=1080)]
    )
    # output.write_videofile("videos/" + str(file_name) + ".mp4" )
    return output
def single_ff(file_name, obj_name, tags, max_length):
    

    min_cli.fget_object("zink", obj_name, file_name)
    probe = ffmpeg.probe(file_name)
    duration = float(probe["streams"][0]["duration"])
    # print(json.dumps(probe["streams"][1], indent=4))
    if duration > max_length or len(probe["streams"]) != 2 :
        return None, 0
    
    user_data = igurl.get(tags["User"]).json()
    
    # print(user_data.get("username"), obj_name)

    pfp_file_path = "images/" + str(tags["User"]) + ".png"
    if (not  os.path.isfile(pfp_file_path)):
        r = requests.get(user_data.get("profile_pic"), stream=True)
        if r.status_code == 200:
            with open(pfp_file_path, "wb") as f:
                for chunk in r:
                    f.write(chunk)
                    
    post_time = datetime.fromtimestamp(int(tags["Timestamp"])/1000, tz=timezone("US/Eastern"))
    time_string = post_time.strftime("%m/%d/%Y, %I:%M:%S %p") #+ (" PM" if post_time.hour >= 12 else " AM")
    left_text = f"{time_string} \n {user_data.get("name") if user_data.get("name") else user_data.get("username") } \n (@{user_data.get("username")})"
    

    input_stream = ffmpeg.input(file_name)
    width, height = (1920, 1080)
    # width, height = (640, 360)
    
    #pad=width=max(iw\,ih*(16/9)):height=ow/(16/9):x=(ow-iw)/2:y=(oh-ih)/2
    # video = input_stream.video.filter("scale", -1,height).filter("pad", width, height, "(ow-iw)/2").filter("setdar", "16/9").filter('drawtext', text=left_text,fontsize=36, x=10,y="(h-text_h)/2",fontcolor="white")
    
    video = input_stream.video.filter("scale", f"min(iw*{height}/ih,{width})",f"min({height},ih*{width}/iw)").filter("pad", width,height,f"({width}-iw)/2", f"({height}-ih)/2").filter("setdar", "16/9").filter('drawtext', text=left_text,fontsize=36, x=10,y="(h-text_h)/2",fontcolor="white")
    # video = input_stream.video.filter("scale", 640,360).filter("setdar", "16/9").filter('drawtext', text=left_text,fontsize=36, x=0,y=0,fontcolor="white")
    video = ffmpeg.filter([video, ffmpeg.input(pfp_file_path)], "overlay", "W-w-10", "H/2 - h/2")
    audio = input_stream.audio 
    if(not audio):
        print("NO AUDIO", audio)
    return ffmpeg.output(video, audio, "videos/" + obj_name.split("/")[-1]), duration

    # return "videos/" + obj_name.split("/")[-1], duration
    # return ffmpeg.input(file_name).filter('drawtext', text=left_text,fontsize=36, x=0,y=0,fontcolor="white").filter("scale", 1920,1080), duration

    

def generate(total_seconds = 300, update_used_tag = False, max_length = 60):
    videos = get_all_videos()
    clips = []
    video_total = 0
    now_timestamp = str(int(time.time()*1000))
    print("NOW TIMESTAMP:", now_timestamp)
    last_generated = "1757185755772"

    for index, o in enumerate(videos):

        if o.object_name.split(".")[-1] != "mp4": 
            #not video
            continue 

        tags = min_cli.get_object_tags("zink", o.object_name)
        # if("Used" in tags):
        #     if(int(tags["Used"]) <= int(last_generated)):
        #         continue
        if("Timestamp" in tags):
            _, week, _ = datetime.fromtimestamp(int(tags["Timestamp"])/1000, tz=timezone("US/Eastern")).isocalendar()
            if(week not in [46]):
                continue
        
        # vid  = single_video(str(index),o.object_name, tags)
        # if vid.duration > max_length:
        #     continue
        
        vid, duration = single_ff("videos/"+str(index) + ".mp4", o.object_name, tags, max_length)
        if not vid:
            continue
        f_name = "videos/" + o.object_name.split("/")[-1]
        if not os.path.exists(f_name):
            # vid.write_videofile(f_name)
            vid.overwrite_output().run()
        if(update_used_tag):
            tags["Used"] = now_timestamp
            print(tags)
            min_cli.set_object_tags("zink",o.object_name, tags)
        # clips.append(vid) 
        clips.append(["videos/" + o.object_name.split("/")[-1], duration])
        video_total += duration
        print("video total: ", video_total)
        if(video_total >= total_seconds):
            return clips
    return clips

def write_to_file(file_name, c):
    final = concatenate_videoclips(c, "compose", bg_color = (0,0,0), padding = 0)
    final.write_videofile(file_name)

def post_video(title, file, description):
    args = Namespace(title=title, 
                    description=description, 
                    file=file, 
                    privacyStatus="unlisted", 
                    noauth_local_webserver = True,
                    logging_level = "ERROR",
                    keywords="",
                    category="22")
    youtube = get_authenticated_service(args)
    try:
        initialize_upload(youtube, args)
    except(HttpError, e):
        print ("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))



# test_video()
title = "Plant Kaiba - Session 28 (Week 46)"
file_name = "test_upload.mp4"
# generate(total_seconds=30, update_used_tag=False)
clips = generate(total_seconds = 3600, update_used_tag=False, max_length = 60)
# GET TIMESTAMPS WORKING? that would be cool
random.shuffle(clips)
# # desc = "\n".join([clip.split(".")[0] for clip in clips])
desc = ""
t = 0 
for i, clip in enumerate(clips):
    desc += f"{convert_second(round(t))} {clip[0].split(".")[0]}\n"
    t += clip[1]
clips = [c[0] for c in clips]

# print("description: ", desc)

clips = [ffmpeg.input(clip) for clip in clips]

video_and_audios_files = [item for sublist in map(lambda f: [f.video, f.audio], clips) for item in sublist]
ffmpeg.concat(*video_and_audios_files, v=1, a=1).output(file_name).overwrite_output().run()

# open('concat.txt', 'w').writelines([('file %s\n' % input_path) for input_path in clips])
# ffmpeg.input('concat.txt', format='concat', safe=0).output(file_name, c='copy').overwrite_output().run()

post_video(title, file_name, desc)
