#!/usr/bin/env python

import sys, os
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

App = flask.Flask(__name__)

App.config.from_object("Config.AppConfig")
App.config["DEBUG"] = True
App.config["FLATPAGES_AUTO_RELOAD"] = App.config["DEBUG"]
App.config["FLATPAGES_EXTENSION"] = u'.md'
App.config["FLATPAGES_ROOT"] = u"contents"
App.config["FREEZER_BASE_URL"] = App.config["APPLICATION_ROOT"]
App.config["FREEZER_DESTINATION"] = u"../build"

class BlogSite(object):
    def __init__(self):
        self.Categories = None
        self.Author = ""
        self.FriendLinks = []

class FrontEndMeta(object):
    def __init__(self, site=None, page_title=""):
        self.Site = site
        self.PageTitle = page_title

Pages = FlatPages(App)
freezer = Freezer(App)

AllCategories = set()
for Page in Pages:
    if "categories" in Page.meta:
        AllCategories.update(set(Page["categories"]))

Site = BlogSite()
Site.Categories = AllCategories
Site.Author = App.config["SITE_AUTHOR"]
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
