import sys, os
import glob
from fabric.api import local
import config

def build():
    # Generate CSS
    AllSCSSs = glob.glob("blog/static/css/*.scss")
    for SCSS in AllSCSSs:
        local("scss {} {}".format(SCSS, os.path.splitext(SCSS)[0] + ".css"))
    # Build contents
    local("blog/blog.py build")

def deploy():
    local("rsync -rlpv --del build/ " + config.Host)

def new():
    import datetime
    Time = datetime.datetime.now()
    Filename = Time.strftime("%Y-%m-%d") + ".md"
    FileDir = os.path.join("blog", "contents", str(Time.year))
    FilePath = os.path.join(FileDir, Filename)
    if not os.path.exists(FileDir):
        os.makedirs(FileDir)
    with open(FilePath, 'w') as NewPage:
        NewPage.write("title:\n")
        NewPage.write("created: " + Time.strftime("%Y-%m-%d %H:%M:%S"))
        NewPage.write("\ncategories: []\n")
        NewPage.write("language:\n")
        NewPage.write("abstract:\n\n")

    local(' '.join((config.Editor, FilePath)))
