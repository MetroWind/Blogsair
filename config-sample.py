# -*- coding: utf-8; -*-
import os

class Link(object):
    def __init__(self, url, name, desc=""):
        self.URL = url
        self.Name = name
        self.Desc = desc

class AppConfig(object):
    SITE_NAME = u"A Blog"
    SITE_AUTHOR = u"Derp"
    APPLICATION_ROOT = "/blog"

PostSort = "created"
PostSortReverse = True

Links = [Link("http://example.com/", "A Site", "A web site"),]
Host = "user@myhost.com:/path/to/my/web/contents"
Editor = os.environ["EDITOR"]
