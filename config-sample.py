# -*- coding: utf-8; -*-
import os

class Link(object):
    def __init__(self, url, name, desc=""):
        self.URL = url
        self.Name = name
        self.Desc = desc

SiteRoot = "/blog"
SiteURIPrefix = "http://example.org"
# Optional: a unique ID for this blog
# SiteID = "some unique stuff"

SiteName = u"A Blog"
SiteAuthor = u"Derp"
SiteAuthorEmail = "foo@example.org"

DefaultLang = "en"

PostSort = "created"
PostSortReverse = True

Links = [Link("http://example.com/", u"A Site", u"A web site"),]
Host = "user@myhost.com:/path/to/my/web/contents"
Editor = os.environ["EDITOR"]
