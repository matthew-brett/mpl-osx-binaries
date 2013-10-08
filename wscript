# waf script
# vim: ft=python
from os.path import join as pjoin
import sys

if sys.version_info[0] == 2:
    from urllib import urlretrieve
    from urlparse import urlparse
else: # Python 3
    from urllib.request import urlretrieve
    from urllib.parse import urlparse

top = '.'
out = 'build'

# External libraries
EXTLIBS = dict(
    zlib = 'http://zlib.net/zlib-1.2.8.tar.gz',
    png =
    'ftp://ftp.simplesystems.org/pub/libpng/png/src/libpng15/libpng-1.5.17.tar.bz2',
    freetype = 'http://download.savannah.gnu.org/releases/freetype/freetype-2.5.0.1.tar.bz2',
)

# Process external libraries
EXTLIBS_PROC = {}
for name, url in EXTLIBS.items():
    val = {}
    parsed = urlparse(url)
    paths = parsed.path.split('/')
    val['url'] = url
    val['tarname'] = paths[-1]
    val['dirname'] = val['tarname'].split('.tar')[0]
    EXTLIBS_PROC[name] = val



def options(opt):
    opt.load('python') # options for disabling pyc or pyo compilation
    opt.load('compiler_c')


def configure(conf):
    conf.load('compiler_c')
    conf.load('python')
    conf.check_python_version((2,7))
    conf.check_python_headers()
    conf.check_python_module('numpy')
    conf.check_python_module('bdist_mpkg')


def fetch(ctx):
    for name, val in EXTLIBS_PROC.items():
        urlretrieve(val['url'], pjoin('archives', val['tarname']))


def build(ctx):
    for name, val in EXTLIBS_PROC.items():
        srcfile = pjoin('archives', val['tarname'])
        srcnode = ctx.path.make_node(srcfile)
        ctx(
            rule           = 'cp ${SRC} ${TGT}',
            source         = srcnode,
            target         = val['tarname'],
        )
