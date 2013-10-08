# waf script
# vim: ft=python
import os
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
# If you update these libraries, run `waf fetch` to fetch them
EXTLIBS = dict(
    zlib = 'http://zlib.net/zlib-1.2.8.tar.gz',
    png =
    'ftp://ftp.simplesystems.org/pub/libpng/png/src/libpng15/libpng-1.5.17.tar.bz2',
    freetype = 'http://download.savannah.gnu.org/releases/freetype/freetype-2.5.0.1.tar.bz2',
)

# Process external library URLs to get archive and directory names
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


def configure(ctx):
    ctx.load('compiler_c')
    ctx.load('python')
    ctx.check_python_version((2,7))
    ctx.check_python_headers()
    ctx.check_python_module('numpy')
    ctx.check_python_module('bdist_mpkg')
    ctx.env.BLD_PREFIX = ctx.path.get_bld().abspath()
    ctx.find_program('touch', var='TOUCH')
    ctx.find_program('touch', var='TOUCH')
    ctx.env.MACOSX_DEPLOYMENT_TARGET='10.6'
    if 'ARCH_FLAGS' in os.environ:
        ctx.env.ARCH_FLAGS=os.environ['ARCH_FLAGS']
    else:
        ctx.env.ARCH_FLAGS = '-arch i386 -arch x86_64'


def fetch(ctx):
    for name, val in EXTLIBS_PROC.items():
        print("Fetching " + val['url'])
        urlretrieve(val['url'], pjoin('archives', val['tarname']))


def build(ctx):
    for name, val in EXTLIBS_PROC.items():
        tarname = val['tarname']
        dirname = val['dirname']
        srcfile = pjoin('archives', tarname)
        srcnode = ctx.path.make_node(srcfile)
        bld_path = ctx.path.get_bld()
        dirnode = bld_path.make_node(dirname)
        tarflag = 'j' if tarname.endswith('bz2') else 'z'
        ctx(
            rule   = 'cp ${SRC} ${TGT}',
            source = srcnode,
            target = tarname,
        )
        ctx(
            rule   = 'tar {0}xvf ${{SRC}}'.format(tarflag),
            source = tarname,
            target = dirnode
        )
        if name == 'zlib':
            ctx(
                rule   = ('cd ${SRC} && '
                          './configure --prefix=${BLD_PREFIX} && '
                          'make -j3 install && '
                          'cd .. && ${TOUCH} ${TGT}'),
                source = dirnode,
                target = 'zlib.stamp',
            )
        elif name == 'png':
            ctx(
                rule   = ('cd ${SRC} && '
                          './configure --disable-dependency-tracking '
                          '--prefix=${BLD PREFIX} && '
                          'make -j3 install && '
                          'cd .. && ${TOUCH} ${TGT}'),
                source = dirnode,
                target = 'png.stamp',
            )
        else: # Freetype
            ctx(
                rule   = ('cd ${SRC} && '
                          './configure --prefix=${BLD_PREFIX} && '
                          'make -j3 && '
                          'make -j3 install && '
                          'cp objs/.libs/libfreetype.a . && '
                          'cd .. && ${TOUCH} ${TGT}'),
                source = dirnode,
                target = 'freetype.stamp',
            )
