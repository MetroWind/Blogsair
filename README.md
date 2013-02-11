# Blogsair

Blogsair is a static blog generator written with the
[Flask](http://flask.pocoo.org/) framework.  Posts are written in
[Markdown](http://daringfireball.net/projects/markdown/), and
converted to HTML with the help of
[Flask-FlatPages](http://packages.python.org/Flask-FlatPages/).
Static codes are generated with
[Frozen-Flask](http://packages.python.org/Frozen-Flask/).

Local management is done with a shell and
[Fabric](http://fabfile.org/).

# Installation

First install Python 2 and all the dependences mentioned above.  Then
put Blogsair somewhere you like, copy ``config-sample.py`` to
``config.py`` and modify it as needed.

Then if you decide to use the style as-is, go to
``blog/static/css/style.scss`` and change the value of variable
``$UrlPrefix`` to the same value of ``APPLICATION_ROOT`` you just
wrote in ``config.py``.

You will probably want to modify the style as well.  It is mainly
defined in ``blog/static/css/style.scss``, which is in
[SCSS](http://sass-lang.com/) syntax.  In Blogsair, each post can have
a language property.  Stylesheets ``type-en.scss`` and
``type-zh.scss`` are presented for English (``en``) and Chinese
(``zh``) posts.  This behavior is currently hard-coded in the
template.  Stylesheet ``syntax.scss`` defines the color scheme of
[Pygments](http://pygments.org/).  The language property is also used
to specify the ``lang`` attribute of the article in the HTML.

Ultimately, you will want to rewrite the whole template, which is in
[Jinja2](http://jinja.pocoo.org/) syntax.

# Usage

To make a new post, go to where you put Blogsair, and type ``fab new``
in a terminal, this will create a new Markdown file in
``blog/contents``.  The file will be named with today’s date, and will
be put inside a directory named with the current year.  Then the
editor you defined in ``config.py`` will be used to open that file.
You can then fill the metadata and start writing.

Each post contains a metadata section in YAML syntax, and a body in
Markdown.  In the body, one may use ``{{ var }}`` to reference a
variable in Python code.  Note that the spaces between brackets and
``var`` are mandatory, and each of them can only be *one* space.  For
example

    ![Grape fruit]({{ url_for('static', filename='path/to/image.jpg') }})

would insert an image, whose URL is retrieved with ``url_for()``.  The
variables that can be used in posts are defined inside the ``page()``
function in ``blog/blog.py``, in the ``varReplace`` line.

A minimal post then would run like thus

    title: Some Post
    created: 2013-01-10 15:17:29
    categories: [Rumble,]
    language: en
    abstract: This is a very short post.
       
    Hello *world*!

Then you may run ``fab build`` to generate static HTML.  They will be
put in the ``build`` directory.  A ``fab deploy`` will rsync the
static content to the remote host you defined in ``config.py``.

# Example

[My blog](http://darksair.org/blog/) is built with Blogsair.
