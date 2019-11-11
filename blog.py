#!/usr/bin/env python3

import sys, os
import string
import subprocess
import copy
import glob
import datetime
import shutil
import logging

if sys.version_info.major < 3:
    from xml.sax.saxutils import quoteattr as htmlEscaped
else:
    from html import escape as htmlEscaped

import yaml

def get_logger(name=__name__, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter("[%(asctime)s %(levelname)s] %(message)s",
                                  "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

Logger = get_logger()

class Template(object):
    def __init__(self, temp_str):
        self.TempStr = temp_str
        self.TagPoses = []
        self._parse()

    def _parse(self):
        CharPrev = None
        CharPrevPrev = None
        State = 0               # 0: normal, 1: in tag
        TagPos = [0, 0]
        TagNestiness = 0

        for Pos in range(len(self.TempStr)):
            Char = self.TempStr[Pos]
            if State == 0:
                if (CharPrev, Char) == ('%', '{') and \
                   CharPrevPrev not in ('\\', '%'):
                    # Find a beginning of tag, change state to "in tag".
                    Logger.debug("Found tag opening at {}.".format(Pos))
                    TagPos[0] = Pos - 1
                    State = 1
                    TagNestiness += 1
            elif State == 1:
                if Char == '}' and CharPrev != '\\':
                    # Find a tag ending.
                    Logger.debug("Found tag ending at {}.".format(Pos))
                    TagPos[1] = Pos + 1
                    self.TagPoses.append(copy.copy(TagPos))
                    TagPos = [0, 0]
                    State = 0
            CharPrevPrev = CharPrev
            CharPrev = Char
        return self

    def hasTag(self):
        return len(self.TagPoses) > 0

    def applyTag(self, begin, end, env):
        Tag = self.TempStr[begin:end]
        TagContent = Tag[2:-1].strip()
        try:
            Result = eval(TagContent, {"__builtins__": None}, env)
        except Exception as Err:
            Logger.warning("Error evaluating tag: {}\nGot error: {}"
                         .format(TagContent, repr(Err)))
            return Tag
        else:
            return str(Result)

    def apply(self, env):
        if not self.hasTag():
            return self.TempStr

        Parts = []

        TagPosIter = iter(self.TagPoses)
        PrevTagEnd = 0

        TagPos = next(TagPosIter)
        while True:
            Parts.append(self.TempStr[PrevTagEnd:TagPos[0]])
            Parts.append(self.applyTag(*TagPos, env))
            PrevTagEnd = TagPos[1]
            try:
                TagPos = next(TagPosIter)
            except StopIteration:
                Parts.append(self.TempStr[PrevTagEnd:])
                return "".join(Parts)

TemplateFilters = {"htmlEscaped": htmlEscaped}

def isStr(obj):
    if sys.version_info.major < 3:
        return isinstance(obj, basestring)
    else:
        return isinstance(obj, str)

class Renderer(object):
    Name = ""

    def __init__(self):
        pass

    def render(self, src, *args, **kargs):
        raise NotImplementedError("Using renderer base class.")

class Markdown(Renderer):
    Name = "markdown"
    def __init__(self):
        super(Markdown, self).__init__()

    def render(self, post, *args, **kargs):
        import markdown
        import markdown.treeprocessors

        def addImgClass(ele):
            if len(ele) == 0:
                return

            if ele[0].tag == "img" and ele.text is None:
                ele.set("class", "ImgWrapper")

            elif len(ele[0]) > 0 and ele[0].tag == 'a' and ele[0][0].tag == "img":
                if ele.text is None and ele[0].text is None:
                    ele.set("class", "ImgWrapper")

            else:
                for SubEle in ele:
                    addImgClass(SubEle)

        class ImgClassAdder(markdown.treeprocessors.Treeprocessor):
            def run(self, root):
                addImgClass(root)

        class ImgClasser(markdown.extensions.Extension):
            def extendMarkdown(self, md, md_globals):
                # Insert instance of 'mypattern' before 'references' pattern
                md.treeprocessors.register(ImgClassAdder(md), 'ImgClasser', 0)

        return markdown.markdown(post.ContentApplied, output_format="html5",
                                 extensions=[ImgClasser(),])

class AsciiDoctor(Renderer):
    Name = "asciidoctor"
    def __init__(self):
        super(AsciiDoctor, self).__init__()

    def render(self, post, *args, **kargs):
        Proc = subprocess.Popen(["asciidoctor", "-a", 'stylesheet!', "-s", "-o",
                                 '-', '-'], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        Html, _ = Proc.communicate(input=post.ContentApplied.encode())
        return Html.decode()

Renderers = dict()
for Renderer in (Markdown, AsciiDoctor):
    Renderers[Renderer.Name] = Renderer

class Configuration(dict):
    DefaultFile = "default.yaml"

    def __init__(self):
        super(Configuration, self).__init__()
        self["Posts"] = dict()
        self["Aggregates"] = dict()
        self["Global"] = dict()

    def updateWithFile(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                Conf = yaml.load(f, Loader=yaml.Loader)
                for Section in self:
                    if Section in Conf:
                        self[Section].update(Conf[Section])

    def loadFromFile(self, filename):
        self.updateWithFile(self.DefaultFile)
        self.updateWithFile(filename)

Config = Configuration()

class MarkupPost(object):
    def __init__(self):
        self.Metadata = None
        self.Renderer = ""
        self.Content = ""       # Pre-render, pre tag-apply
        self.ContentApplied = "" # Pre-render, after tag apply
        self.Uri = ""
        self.File = ""
        self.Rendered = ""
        self.Time = None
        self._Updated = None

    @property
    def Updated(self):
        if self._Updated is None:
            return self.Time
        else:
            return self._Updated

    @staticmethod
    def _str2Time(time_str):
        try:
            return datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")

    def loadFromFile(self, filename):
        LinesHeader = []
        LinesContent = []
        InHeader = True
        with open(filename, 'r') as PostFile:
            for Line in PostFile:
                if Line.strip() == "" and InHeader is True:
                    InHeader = False
                    continue

                if InHeader is True:
                    LinesHeader.append(Line)
                else:
                    LinesContent.append(Line)

        self.Metadata = yaml.load("".join(LinesHeader), Loader=yaml.Loader)
        self.Content = "".join(LinesContent)
        self.File = filename
        if isinstance(self.Metadata["Time"], datetime.datetime):
            self.Time = self.Metadata["Time"]
            self.Metadata["Time"] = self.Time.strftime("%Y-%m-%d %H:%M")
        else:
            self.Time = self._str2Time(self.Metadata["Time"])

        if "Updated" in self.Metadata:
            self._Updated = self._str2Time(self.Metadata.get("Updated"))

        if "Renderer" in self.Metadata:
            self.Renderer = self.Metadata["Renderer"]
        else:
            self.Renderer = Config["Posts"]["Renderer"]

    def env(self):
        TempDict = copy.deepcopy(TemplateFilters)
        TempDict.update(Config["Global"])
        TempDict.update(Config["Posts"])
        TempDict.update(self.Metadata)
        TempDict["Time"] = self.Time.strftime("%Y-%m-%d %H:%M")
        TempDict["TimeObj"] = self.Time
        TempDict["Content"] = self.Rendered
        TempDict["Uri"] = self.Uri
        return TempDict

    def render(self):
        """Render `self.Content` and save result to `self.Rendered`."""

        RenderConfig = self.Renderer
        RenderArgs = []
        RenderKargs = dict()
        if isStr(RenderConfig):
            Renderer = Renderers[RenderConfig]()
        elif isinstance(RenderConfig, (list, tuple)):
            Renderer = Renderers[RenderConfig[0]]()
            RenderArgs = RenderConfig[1:]
        elif isinstance(RenderConfig, dict):
            Renderer = Renderers[RenderConfig["Name"]]()
            RenderKargs = RenderConfig

        else:
            raise RuntimeError("Invalid renderer specification: "
                               + str(RenderConfig))

        self.ContentApplied = Template(self.Content).apply(self.env())
        self.Rendered = Renderer.render(self, *RenderArgs, **RenderKargs)

class Aggregation(object):
    ConfigFileBaseName = "config.yaml"

    def __init__(self, base_dir):
        self.BaseDir = base_dir
        self.FrameTemp = None   # type: Template
        self.BodyTemp = None    # type: Template
        self.Output = ""
        self._load(base_dir)
        self.Rendered = ""
        self.Options = dict()

    def _load(self, base_dir):
        with open(os.path.join(base_dir, self.ConfigFileBaseName), 'r') as f:
            Config = yaml.load(f, Loader=yaml.Loader)

        with open(os.path.join(base_dir, Config["Frame"]), 'r') as f:
            self.FrameTemp = Template(f.read())
        with open(os.path.join(base_dir, Config["Body"]), 'r') as f:
            self.BodyTemp = Template(f.read())

        self.Output = Config["Output"]

        if "Options" in Config:
            self.Options = Config["Options"]

        return self

    def render(self, posts):
        Body = []
        for Post in posts:
            Body.append(self.BodyTemp.apply(Post.env()))

        Env = copy.deepcopy(TemplateFilters)
        Env.update(Config["Global"])
        Env.update(Config["Aggregates"])
        Env["Body"] = "".join(Body)
        Env["Updated"] = max(p.Updated for p in posts)
        self.Rendered = self.FrameTemp.apply(Env)
        return self.Rendered

class DocumentSite(object):
    def __init__(self):
        Conf = Config["Global"]
        self.SrcRoot = Conf["SrcRoot"]
        self.RenderedRoot = Conf["RenderedRoot"]
        self.PostTemplateRoot = Conf["PostTemplateRoot"]
        self.AggrTemplateRoot = Conf["AggrTemplateRoot"]
        self.PostTemplate = "post.html"
        self.StaticRoot = Conf["StaticRoot"]
        self.StaticDest = Conf["StaticDest"]
        self.Title = ""
        self.Posts = []
        self.Aggregates = []

    def renderPosts(self):
        # Get a list of all posts
        for DirInfo in os.walk(self.SrcRoot, followlinks=True):
            for File in DirInfo[2]:
                if File.startswith('.'):
                    continue
                FullPath = os.path.join(DirInfo[0], File)
                Logger.debug("Rendering {}...".format(FullPath))
                Post = MarkupPost()
                Post.loadFromFile(FullPath)
                RelPath = FullPath[len(self.SrcRoot):]
                if RelPath.startswith('/'):
                    RelPath = RelPath[1:]
                Post.Uri = os.path.splitext(RelPath)[0]
                self.Posts.append(Post)

        self.Posts.sort(key=lambda p: p.Time, reverse=True)

        # Render all posts.
        for Post in self.Posts:
            Post.render()

        # Apply post template
        with open(os.path.join(self.PostTemplateRoot, self.PostTemplate),
                  'r') as TempFile:
            PostTempStr = TempFile.read()

        PostTemp = Template(PostTempStr)
        for Post in self.Posts:
            Result = PostTemp.apply(Post.env())

            # Write HTML
            OutputDir = os.path.join(self.RenderedRoot, Post.Uri)
            if not os.path.exists(OutputDir):
                os.makedirs(OutputDir)

            with open(os.path.join(OutputDir, "index.html"), 'w') as HtmlFile:
                HtmlFile.write(Result)

    def renderAggregates(self):
        AggrDirs = []
        for Dir in os.listdir(self.AggrTemplateRoot):
            TrueDir = os.path.join(self.AggrTemplateRoot, Dir)
            if os.path.isdir(TrueDir):
                AggrDirs.append(TrueDir)

        Aggrs = []
        for Dir in AggrDirs:
            Aggrs.append(Aggregation(Dir))
        self.Aggregates = Aggrs

        for Aggr in self.Aggregates: # type: Aggregation
            Aggr.render(self.Posts)
            with open(os.path.join(self.RenderedRoot, Aggr.Output), 'w') as Output:
                Output.write(Aggr.Rendered)

    def copyStatic(self):
        for DirInfo in os.walk(self.StaticRoot, followlinks=True):
            for File in DirInfo[2]:
                FullPath = os.path.join(DirInfo[0], File)
                RelPath = FullPath[len(self.StaticRoot):]
                if RelPath.startswith('/'):
                    RelPath = RelPath[1:]
                Dest = os.path.join(self.RenderedRoot, self.StaticDest, RelPath)
                DestDir = os.path.dirname(Dest)
                if not os.path.exists(DestDir):
                    os.makedirs(DestDir)
                shutil.copy(FullPath, Dest)

    def render(self):
        self.renderPosts()
        self.renderAggregates()
        self.copyStatic()

def test():
    Site = DocumentSite()
    Site.render()

def build(args):
    if args.OptsGlobal:
        for Opt, Value in args.OptsGlobal:
            Config["Global"][Opt] = Value

    if args.BuildLocal:
        Config["Global"]["UriPrefixNoProto"] = os.path.join(
            os.getcwd(), Config["Global"]["RenderedRoot"])

    if os.path.exists(Config["Global"]["RenderedRoot"]):
        shutil.rmtree(Config["Global"]["RenderedRoot"])

    # Generate CSS
    AllSCSSs = glob.glob("static/css/*.scss")
    for SCSS in AllSCSSs:
        subprocess.check_call("sassc {} {}".format(
            SCSS, os.path.splitext(SCSS)[0] + ".css"),
                              shell=True)
    os.makedirs(Config["Global"]["RenderedRoot"])
    Site = DocumentSite()
    Site.render()

def deploy(args):
    subprocess.check_call(["rsync", "-rlpv", "--del",
                           Config["Global"]["RenderedRoot"] + '/',
                           Config["Global"]["Host"]])

def newPost(_):
    """Create a new post and start editing."""
    Time = datetime.datetime.now()
    Filename = Time.strftime("%Y-%m-%d") + ".md"
    FileDir = os.path.join(Config["Global"]["SrcRoot"], "p", str(Time.year))
    FilePath = os.path.join(FileDir, Filename)
    if not os.path.exists(FileDir):
        os.makedirs(FileDir)
    with open(FilePath, 'w') as NewPage:
        NewPage.write("Title:\n")
        NewPage.write("Time: " + Time.strftime("%Y-%m-%d %H:%M"))
        NewPage.write("\nCategories: []\n")
        NewPage.write("Language:\n")
        NewPage.write("Abstract:\n\n")

    subprocess.check_call(' '.join(('emacsclient', "-n", FilePath)), shell=True)

def main():
    global Config
    import argparse

    Parser = argparse.ArgumentParser(description='Generate blog.')
    Parser.add_argument('--set-global', dest='OptsGlobal', nargs=2, action="append",
                             metavar=("OPT", "VALUE"),
                             help='Set global option OPT to VALUE.')
    SubParsers = Parser.add_subparsers(title="Commands")
    ParserBuild = SubParsers.add_parser("build")
    ParserBuild.set_defaults(func=build)
    ParserBuild.add_argument("-l", '--local', dest='BuildLocal', default=False,
                             action="store_true",
                             help='Build a local blog. This overides the '
                             '"UriPrefixNoProto" global parameter.')
    ParserDeploy = SubParsers.add_parser("deploy")
    ParserDeploy.set_defaults(func=deploy)
    ParserNew = SubParsers.add_parser("new")
    ParserNew.set_defaults(func=newPost)

    Args = Parser.parse_args()

    Config.loadFromFile("config.yaml")
    Config.updateWithFile("user.yaml")
    Args.func(Args)

    return 0

if __name__ == "__main__":
    sys.exit(main())
