from datetime import date, datetime, time
import sys
from flask import Flask, render_template, Response, redirect, \
        url_for, request
from flask_bootstrap import Bootstrap
from flask_flatpages import FlatPages, pygments_style_defs
from flask_frozen import Freezer
from operator import itemgetter
from urlparse import urljoin
from werkzeug.contrib.atom import AtomFeed

DEBUG = True
FLATPAGES_AUTO_RELOAD = DEBUG
FLATPAGES_EXTENSION = '.md'
FLATPAGES_ROOT = 'content'
FLATPAGES_MARKDOWN_EXTENSIONS = ['extra', 'codehilite', 'footnotes',
    'fenced_code', 'smart_strong', 'smarty', 'tables', 'toc',
    'wikilinks']
PAGE_SIZE = 100
FREEZER_BASE_URL = "http://blog.shatow.net"

from markdown import util
from markdown import preprocessors
import re
old_preprocessor = preprocessors.NormalizeWhitespace.run
def fix_markdown_NormalizeWhitespace(self, lines):
    source = '\n'.join(lines)
    source = source.replace(util.STX, "").replace(util.ETX, "")
    source = source.replace("\r\n", "\n").replace("\r", "\n") + "\n\n"
    # this code is broken https://github.com/waylan/Python-Markdown/issues/36
    #source = source.expandtabs(self.markdown.tab_length)
    source = re.sub(r'(?<=\n) +\n', '\n', source)
    return source.split('\n')

preprocessors.NormalizeWhitespace.run = fix_markdown_NormalizeWhitespace

app = Flask(__name__)
pages = FlatPages(app)
freezer = Freezer(app)
Bootstrap(app)
app.config.from_object(__name__)

@app.context_processor
def inject_globals():
    all_tags = set([
        taglist
        for page in pages
        for taglist in page.meta.get('tags', [])
        ])
    """
    all_tags = {}
    for tag in tags:
        if tag not in all_tags:
            all_tags[tag] = 1
        else:
            all_tags[tag] = all_tags[tag] + 1
    """
    recent_posts = _find_posts()

    return {
            'all_tags': all_tags,
            'recent_posts': recent_posts,
            'year': date.today().year
            }

@app.template_filter('truncate_more')
def _truncate_more_filter(post):
    more = post.html.find('<!--more-->')
    if more == -1:
        return ""
    return post.html[0:more]

def _find_posts(tag=None):
    if tag is not None:
        posts = [p for p in pages if tag in p.meta.get('tags', [])]
    else:
        posts = [p for p in pages]
    posts.sort(key=itemgetter('date'), reverse=True)
    return posts

def chunks(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def page_chunks(l, page_size, page):
    chunked_pages = chunks(l, page_size)
    return list(chunked_pages)[page - 1]

@app.route("/")
def index():
    posts = page_chunks(list(_find_posts()), PAGE_SIZE,
            int(request.args.get('page', 1)))
    return render_template('posts.html', posts=posts)

@app.route('/<path:path>/')
def post(path):
    post = pages.get_or_404(path)
    return render_template('post.html', post=post)

def _export_post(post, export_type=None):
    if export_type == 'html':
        content = post.html
    else:
        content = post.body
    return content.replace("<!--more-->\n", '') + \
            "\n\nCopyright %s Bryan Drewery" % (post.meta['date'])

@app.route('/<path:path>.md')
@app.route('/<path:path>.txt')
def post_raw(path):
    post = pages.get_or_404(path)
    return Response(
            _export_post(post),
            mimetype='text/plain')
    return render_template('post.html', post=post)

@app.route('/tag/<string:tag>/')
def tag(tag):
    posts = _find_posts(tag)
    return render_template('tag.html', posts=posts, tag=tag)


@app.route('/recent.atom')
def recent_feed():
    feed = AtomFeed('Recent Articles',
            feed_url=request.url, url=request.url_root)
    posts = page_chunks(list(_find_posts()), 15, 1)
    for post in posts:
        feed.add(post.meta['title'],
                _export_post(post, 'html'),
                content_type='html',
                author="Bryan Drewery",
                url=url_for('post', path=post.path, external=True),
                updated=datetime.combine(post.meta['date'], time()),
                published=datetime.combine(post.meta['date'], time()))
    return feed.get_response()

# Handle legacy site redirects
@app.route('/<path:path>.markdown')
def post_legacy_link(path):
    path = path.replace('post/', 'posts/')
    post = pages.get_or_404(path)
    return render_template('redirect.html', url=url_for('post', path=path))

@freezer.register_generator
def generate_legacy_link():
    posts = _find_posts()
    for post in posts:
        if post.meta['date'].year < 2014:
            yield 'post_legacy_link', \
            {'path': post.path.replace('posts/', 'post/')}

@freezer.register_generator
def generate_post_raw():
    posts = _find_posts()
    for post in posts:
        yield 'post_raw', {'path': post.path}

@app.route('/static/pygments.css')
def pygments_css():
    return pygments_style_defs('tango'), 200, {'Content-Type': 'text/css'}

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        freezer.freeze()
    else:
        app.run(host='0.0.0.0', port=5001, debug=True)
