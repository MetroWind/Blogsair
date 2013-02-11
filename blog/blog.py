#!/usr/bin/env python

import sys, os
import urlparse as URLParse
import imp

import flask
from flask_flatpages import FlatPages
from flask_frozen import Freezer
# Import the config module
Config = imp.load_source("Config", os.path.join(os.path.dirname(__file__), "..", "config.py"))

def varReplace(content, var_dict):
    Cont = content
    PatternBegin = 0
    while True:
        PatternBegin = Cont.find('{{', PatternBegin)
        if PatternBegin == -1:
            break
        VarBegin = PatternBegin + 3
        PatternEnd = Cont.find('}}', PatternBegin)
        PatternEnd += 2
        VarEnd = PatternEnd - 3
        Pattern = Cont[PatternBegin:PatternEnd]
        Var = Cont[VarBegin:VarEnd]
        Cont = Cont.replace(Pattern, eval(Var, var_dict))
    Cont = Cont.replace("\\{", '{')
    Cont = Cont.replace("\\}", '}')
    return Cont

def sortPosts(posts):
    return sorted(posts, key=lambda x: x[Config.PostSort],
           reverse=Config.PostSortReverse)

def dateTime2ISO8601Format(dt):
    if dt.tzname():
        return dt.isoformat()
    else:
        return dt.isoformat() + 'Z'

App = flask.Flask(__name__)

App.config["APPLICATION_ROOT"] = Config.SiteRoot
App.config["DEBUG"] = True
App.config["FLATPAGES_AUTO_RELOAD"] = App.config["DEBUG"]
App.config["FLATPAGES_EXTENSION"] = u'.md'
App.config["FLATPAGES_ROOT"] = u"contents"
App.config["FREEZER_BASE_URL"] = App.config["APPLICATION_ROOT"]
App.config["FREEZER_DESTINATION"] = u"../build"

class BlogSite(object):
    def __init__(self):
        self.Name = ""
        self.Categories = None
        self.Author = ""
        self.AuthorEmail = ""
        self.FriendLinks = []

class FrontEndMeta(object):
    def __init__(self, site=None, page_title=""):
        self.Site = site
        self.PageTitle = page_title
        self.DefaultLang = Config.DefaultLang

Pages = FlatPages(App)
freezer = Freezer(App)

AllCategories = set()
for Page in Pages:
    if "categories" in Page.meta:
        AllCategories.update(set(Page["categories"]))

Site = BlogSite()
Site.Name = Config.SiteName
Site.URIPrefix = Config.SiteURIPrefix
Site.Categories = AllCategories
Site.Author = Config.SiteAuthor
Site.AuthorEmail = Config.SiteAuthorEmail
Site.FriendLinks = Config.Links

@App.route("/")
def index():
    Meta = FrontEndMeta(Site)
    return flask.render_template("index.html", pages=sortPosts(Pages), meta=Meta)

@App.route("/<page>/")
def htmlPage(page):
    Meta = FrontEndMeta(Site, page.title())
    return flask.render_template("{}.html".format(page), pages=Pages, meta=Meta)

@App.route('/p/<path:path>/')
def page(path):
    Page = Pages.get_or_404(path)

    Page.body = varReplace(Page.body, {"app_root": App.config["APPLICATION_ROOT"],
                                       "url_for": flask.url_for})
    Meta = FrontEndMeta(Site, Page["title"])
    return flask.render_template("post.html", page=Page, meta=Meta)

@App.route('/cat/<cat>/')
def category(cat):
    CatPages = sortPosts([p for p in Pages if cat in p.meta.get('categories', [])])
    Meta = FrontEndMeta(Site, ':'+cat)
    return flask.render_template("category.html", pages=CatPages, category=cat,
                                 meta=Meta)

@App.route('/atom.xml')
@App.route('/feed.xml')
def feed():
    Meta = FrontEndMeta(Site)
    Posts = sortPosts(Pages)[:10]

    # Generate a unique ID for the site.
    DomainName = URLParse.urlparse(Site.URIPrefix).hostname
    if hasattr(Config, "SiteID"):
        Meta.Site.FeedID = SiteID
    else:
        Meta.Site.FeedID = Site.URIPrefix + Config.SiteRoot

    def urlForWithDomain(endpoint, **values):
        return Site.URIPrefix + flask.url_for(endpoint, **values)
    for Post in Posts:
        # Generate unique IDs for each post, and generate the
        # creation/update time in iso format.
        CreationTime = Post["created"]
        CreationTimeISO = dateTime2ISO8601Format(CreationTime)
        Post.FeedID = "tag:{},{}:{}".format(DomainName, CreationTime.year, CreationTimeISO)
        Post.CreatedISO = CreationTimeISO
        if "updated" in Post.meta:
            UpdateTime = Post["updated"]
            Post.UpdatedISO = dateTime2ISO8601Format(UpdateTime)
        else:
            Post.UpdatedISO = ""

        # Derefernece the variables in articles.  We cannot use
        # flask.url_for, because we need absolute URLs.
        Post.body = varReplace(Post.body, {"app_root": App.config["APPLICATION_ROOT"],
                                           "url_for": urlForWithDomain})

    # Acquire the update time for the site.
    Meta.Site.Updated = max([p.UpdatedISO for p in Posts] \
                            + [p.CreatedISO for p in Posts])

    Response = flask.make_response(flask.render_template("feed.xml", pages=Posts, meta=Meta))
    Response.mimetype = "application/atom+xml"
    return Response

@freezer.register_generator
def feed_url_generator():
    return ("/feed.xml", "/atom.xml")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        freezer.freeze()
    else:
        from werkzeug.serving import run_simple
        from werkzeug.wsgi import DispatcherMiddleware
        Application = DispatcherMiddleware(flask.Flask('dummy_app'), {
            App.config['APPLICATION_ROOT']: App,
            })

        run_simple('localhost', 8000, Application, use_reloader=True)
