download-reddit-saved-images for NSFW posts
============================

This script checks your saved links and searchs for images to automagically download them into a folder.

Instructions
---
1. Clone the repository
2. Open config.yaml and configure your data. Username and password to login, and directory to store images.
3. Run the script and see how your saved images are downloaded :)


Changelog
---
    * Added gfycat download and fixed imgur album downloads by using the imgur gallery


Support
---
1. Direct links to images
2. Imgur links
3. Imgur albums (fixed)
4. Flickr images
5. Tumblr  (not fully tested)
6. Picsarus
7. Picasaurus
8. gfycat



**Note**: Gifs seems to not work.


**If you want to collaborate, to improve performance or to add support to another websites, please submit pull requests.**


Requirements
---
1. BeautifulSoup 4
2. Requests
3. Praw
4. PIL
5. PyYAML
6. imgurpython
