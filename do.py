#!/usr/bin/env python3

from __future__ import print_function

import sys, os
import glob
import subprocess
import datetime

import config

def run(cmd):
    subprocess.check_call(cmd, shell=True)

def build():
    # Generate CSS
    AllSCSSs = glob.glob("blog/static/css/*.scss")
    for SCSS in AllSCSSs:
        run("scss -C {} {}".format(SCSS, os.path.splitext(SCSS)[0] + ".css"))
    # Build contents
    run("blog/blog.py build")

def deploy():
    run("rsync -rlpv --del build/ " + config.Host)

def new():
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

    run(' '.join((config.Editor, FilePath)))

ActionFuncs = (build, deploy, new)
Actions = {f.__name__: f for f in ActionFuncs}

Parser = argparse.ArgumentParser(description='Do some action.')
Parser.add_argument('Action', metavar='ACTION', type=str, nargs='?',
                   help='The action to perform.')
Parser.add_argument('Arguments', metavar='ARG', type=str, nargs='*',
                   help='Argument for the action.')
Parser.add_argument('-l', '--list', dest='List', action='store_true',
                   help='List available actions.')

Args = Parser.parse_args()
if Args.List:
    print("All actions:")
    print()
    for Act in Actions:
        print("- {}: {}".format(Act, Actions[Act].__doc__))
    sys.exit()

if Args.Action:
    if Args.Action in Actions:
        Actions[Args.Action](*(Args.Arguments))
    else:
        print("Error: Unknown action:", Args.Action, file=sys.stderr)
        sys.exit(1)
