"""
Python script to download saved images from reddit
"""
from __future__ import print_function
import requests
import os
from glob import glob
from bs4 import BeautifulSoup as bs
from zipfile import ZipFile
from PIL import Image
import praw
try:
    from io import BytesIO
except ImportError:
    from StringIO import BytesIO
import time
import yaml
import re
from imgur import ImgurDownloader
import json

__author__ = 'Adrian Espinosa'
__version__ = '2.0.3'
__contributor__ = '/u/shaggorama'

IMAGE_FORMATS = ['bmp', 'dib', 'eps', 'ps', 'gif', 'im', 'jpg', 'jpe', 'jpeg',
                 'pcd', 'pcx', 'png', 'pbm', 'pgm', 'ppm', 'psd', 'tif',
                 'tiff', 'xbm', 'xpm', 'rgb', 'rast', 'svg']

CONFIG = open('config.yaml')
CONFIG_DATA = yaml.safe_load(CONFIG)
# user data
USERNAME = CONFIG_DATA['username']
PASSWORD = CONFIG_DATA['password']
SAVE_DIR = CONFIG_DATA['save_dir']
REDDIT_CLIENTID = CONFIG_DATA['reddit_clientid']
REDDIT_CLIENTSECRET = CONFIG_DATA['reddit_clientsecret']
IMGUR_CLIENTID = CONFIG_DATA['imgur_clientid']
IMGUR_CLIENTSECRET = CONFIG_DATA['imgur_clientsecret']
ALBUM_PATH = os.path.join(SAVE_DIR, 'albums')

# to notify ERRORS
ERRORS = []
# list to append correct submissions
# at the end, iterate through the list unsaving them
# It seems that removing items just after being downloaded
# causes to fetch just the first page
CORRECT_SUBMISSIONS = []


class Downloader(object):
    """
    Downloader class.
    Define here all methods to download images from different hosts or
    even direct link to image
    """
    # global ERRORS

    def safe_filename(self, filename):
        one = re.sub(r'[\\\\/*?:"<>|]',"",filename)
        two = re.sub(r'[\[\]]', '', one)
        return two

    def http_normalize_slashes(self, url):
        url = str(url).encode('utf-8')
        segments = url.split('/')
        correct_segments = []
        for segment in segments:
            if segment != '':
                correct_segments.append(segment)
        first_segment = str(correct_segments[0])
        if first_segment.find('http') == -1:
            correct_segments = ['http:'] + correct_segments
        correct_segments[0] = correct_segments[0] + '/'
        normalized_url = '/'.join(correct_segments)
        return normalized_url

    def __init__(self, submission):
        self.submission = submission
        try:
            self.submission.url = self.http_normalize_slashes(self.submission.url)
        except:
            print("STRANGE UNICODE!")
        self.path = os.path.join(SAVE_DIR, str(submission.created) + " " +
                                 self.safe_filename(submission.title.encode('utf-8')+" %"+ str(submission.subreddit)+"%")
                                 .replace("/", "")
                                 .replace("\\", "")).replace('"', "")
        self.album_path = os.path.join(self.path, 'albums')
        if(self.submission.over_18):
            print("Downloading --> {0}".format(submission.title.encode('utf-8')[0:60]))

    def is_image_link(self, sub):
        """
        Takes a praw.Submission object and returns a boolean
        describing whether or not submission links to an
        image.
        """
        if sub.url.split('.')[-1] in IMAGE_FORMATS:
            return True
        else:
            return False

    def check_if_image_exists(self, path, is_file=True):
        """
        Takes a path an checks whether it exists or not.
        param: is_file: Used to determine if its a full name
        (/Users/test.txt) or a pattern (/Pics/myphoto*)
        """
        try:
            return os.path.isfile(path) if is_file else len(glob(path + '*')) >= 1
        except Exception as e:
            print(e)
            print(path)
            input("CRASH!")

    def download_and_save(self, url, custom_path=None):
        """
        Receives an url.
        Download the image (bytes)
        Store it.
        """
        if not custom_path:
            path = self.path
        else:
            path = custom_path

        if not self.check_if_image_exists(path, is_file=False):
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            img.verify()
            if not custom_path:
                path = self.path + "." + img.format.lower()
            else:
                path = custom_path + "." + img.format.lower()
            Image.open(BytesIO(response.content)).save(path)
        else:
            print('%s exists, not saving.' % self.submission.title
                  .encode('utf-8'))

        CORRECT_SUBMISSIONS.append(self.submission)

    def gfycat_link(self):
        #First make the link how we want it.
        if not self.check_if_image_exists(self.path, is_file=False):
            url = self.submission.url
            if ".gfycat" not in url: #If .gfycat exists the url is already right.
                if "gifs/detail" in url:
                    url = url.replace("gifs/detail","cajax/get") #Makes detail posts into json link instead
                else:
                    url = url.replace("https://gfycat.com/", "https://gfycat.com/cajax/get/") #changes entire url to json link
                r = requests.get(url)
                data = json.loads(r.content)
                url = data['gfyItem']['webmUrl']

            r = requests.get(url)
            f=open(self.path + ".webm",'wb');
            for chunk in r.iter_content(chunk_size=255): 
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
            f.close()
            CORRECT_SUBMISSIONS.append(self.submission)
        else:
            print('%s exists, not saving.' % self.submission.title
                  .encode('utf-8'))

    def direct_link(self):
        """
        Direct link to image
        """
        try:
            self.download_and_save(self.submission.url)
        except Exception as ex:
            ERRORS.append(self.submission.title.encode('utf-8'))
            print(ex)

    def imgur_album(self):
        """
        Album from imgur
        """
        download_url = 'https://s.imgur.com/a/%s/zip' % \
            (os.path.split(self.submission.url)[1])
        try:
            response = requests.get(download_url)
            #print(len(response.content))
            #print(download_url)
        except Exception as e:
            response = ""
            print(e)

        path = os.path.join(ALBUM_PATH, self.safe_filename(self.submission.title+" %"+str(self.submission.subreddit)+"%")
                            .encode('utf-8')[0:50].replace("/", ""))
        print(path)
        # extract zip
        if not os.path.exists(path):
            os.mkdir(path)
        try:
            # i = open(path + '.zip', 'w')
            # i.write(StringIO(response.content))
            # i.close()
            zipfile = ZipFile(BytesIO(response.content))
            zipfile.extractall(path)
            CORRECT_SUBMISSIONS.append(self.submission)
        except Exception as ex:  # big album
            try:
                os.remove(path + '.zip')
            except OSError as ex:
                ERRORS.append(self.submission.title.encode('utf-8'))
                print("Zip does not seem to be working... Switching to 'manual'")
            #print("Exception: {0}".format(str(ex)))
            print("Downloading each image...")
            # this is the best layout
            idimage = os.path.split(self.submission.url)[1]
            if '#' in idimage:
                print("# in idimage")
                idimage = idimage[0:idimage.index("#")]
            
            links = imgurclient.GetAlbumLinks(idimage)
            counter = 0
            if(links != None):
                for link in links:
                    try:
                        print("Processing {0}".format(link))
                        self.download_and_save(link, custom_path=path +
                                                   "/" + str(counter) + " - " + self.safe_filename(self.submission.title.encode('utf-8')))
                    except Exception as ex:
                        ERRORS.append(self.submission.title.encode('utf-8'))
                        print("Exception: {0}".format(str(ex)))
                    counter += 1
            CORRECT_SUBMISSIONS.append(self.submission)
            #input("tt")

    def imgur_link(self):
        """
        Image from imgur
        """
        # just a hack. i dont know if this will be a .jpg, but in order to
        # download an image data, I have to write an extension
        new_url = "http://i.imgur.com/%s.jpg" % \
            (os.path.split(self.submission.url)[1])
        try:
            self.download_and_save(new_url)
        except Exception as ex:
            ERRORS.append(self.submission.title.encode('utf-8'))
            print(ex)

    def tumblr_link(self):
        """
        Tumblr image link
        """
        response = requests.get(self.submission.url)
        soup = bs(response.content)
        # div = soup.find("div", {'class': 'post'})
        # if not div:
        #     div = soup.find("li", {'class': 'post'})
        img_elements = soup.findAll("img")
        for img in img_elements:
            if "media.tumblr.com/tumblr_" in img.attrs['src']:
                img_url = img.attrs['src']
                # img = div.find("img")
                # img_url = img.attrs["src"]
                try:
                    self.download_and_save(img_url)
                except Exception as ex:
                    ERRORS.append(self.submission.title.encode('utf-8'))
                    print(ex)

    def flickr_link(self):
        """
        Flickr image link
        """
        response = requests.get(self.submission.url)
        soup = bs(response.content)
        div_element = soup.find("div", {"class": "photo-div"})
        img_element = div_element.find("img")
        img_url = img_element.attrs['src']
        try:
            self.download_and_save(img_url)
        except Exception as ex:
            ERRORS.append(self.submission.title.encode('utf-8'))
            print(ex)

    def picsarus_link(self):
        """
        Picsarus image link
        """
        try:
            self.download_and_save(self.submission.url + ".jpg")
        except Exception as ex:
            ERRORS.append(self.submission.title.encode('utf-8'))
            print(ex)

    def picasaurus_link(self):
        """
        Picasaurus image link
        """
        response = requests.get(self.submission.url)
        soup = bs(response.content)
        img = soup.find("img", {"class": "photoQcontent"})
        img_url = img.attrs['src']
        try:
            self.download_and_save(img_url)
            CORRECT_SUBMISSIONS.append(self.submission)
        except Exception as ex:
            ERRORS.append(self.submission.title.encode('utf-8'))
            print(ex)

    def choose_download_method(self):
        """
        This method allows to decide how to process the image
        """
        if(not self.submission.over_18):
            return

        videosites = ['xhamster.com', 'pornhub.com', 'worldsex.com', 'xvideos.com', 'cz.pornhub.com', 'spankbang.com']
        if self.is_image_link(self.submission):
            self.direct_link()
        else:
            # not direct, read domain
            if 'imgur' in self.submission.domain:
                # check if album
                if '/a/' in self.submission.url:
                    self.imgur_album()
                else:
                    self.imgur_link()
            elif 'tumblr' in self.submission.domain:
                self.tumblr_link()
            elif 'flickr' in self.submission.domain:
                self.flickr_link()
            elif 'picsarus' in self.submission.domain:
                self.picsarus_link()
            elif 'picasaurus' in self.submission.domain:
                self.picasaurus_link()
            elif 'gfycat' in self.submission.domain:
                self.gfycat_link()
            elif 'redditmedia' in self.submission.domain:
                self.direct_link()
            elif self.submission.domain in videosites:
                file = open("downloadvideos.txt","a") 
                file.write("start /WAIT youtube-dl.exe -c " + self.submission.url + "\n")
                file.close()
            else:
                if("self." not in self.submission.domain):
                    file = open("testfile.txt","a") 
                    file.write(self.submission.domain + "\n")
                    file.close()
                
                print("%s ->> Domain not supported" % (self.submission.domain))
imgurclient = ImgurDownloader(IMGUR_CLIENTID, IMGUR_CLIENTSECRET)
#R = praw.Reddit("bot1", user_agent="aesptux\'s saved images downloader") #Login
R = praw.Reddit(client_id=REDDIT_CLIENTID,
                client_secret=REDDIT_CLIENTSECRET,
                user_agent="Logon\'s saved images downloader heavily based on aesptux\'s work.",
                username=USERNAME,
                password=PASSWORD)
#print(help(R.user.me()))
print("Logging in...")
# create session
#R.login(username=USERNAME, password=PASSWORD)
print("Logged in.")
print("Getting data...")
file = open("downloadvideos.txt","w")
file.close()
file = open("testfile.txt","w") 
file.close()
# this returns a generator
SAVED_LINKS = R.user.me().saved(limit=None)
# check if dir exists
if not os.path.exists(SAVE_DIR):
    os.mkdir(SAVE_DIR)
if not os.path.exists(os.path.join(SAVE_DIR, 'albums')):
    os.mkdir(ALBUM_PATH)

for link in SAVED_LINKS:
    #print(type(link))
    if type(link) is praw.models.reddit.submission.Submission:
        # delete trailing slash
        if link.url.endswith('/'):
            link.url = link.url[0:-1]
        # create object per submission. Trusting garbage collector!
        d = Downloader(link)
        d.choose_download_method()

print("Done.")

# unsave items
#for c_submission in CORRECT_SUBMISSIONS:
#    print("Unsaving %s" % (c_submission.title.encode('utf-8')))
#    c_submission.unsave()
#    time.sleep(2)  # reddit's api restriction

if len(ERRORS) > 0:
    print("The following items have failed:")
    for err in ERRORS:
        print(err)
    print("Perhaps you should check if the images still exist.")
