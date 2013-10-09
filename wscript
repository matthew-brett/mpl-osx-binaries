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
    bld_path = ctx.path.get_bld().abspath()
    ctx.env.BLD_PREFIX = bld_path
    ctx.find_program('touch', var='TOUCH')
    # Prepare environment variables
    sys_env = dict(os.environ)
    sys_env['MACOSX_DEPLOYMENT_TARGET']='10.6'
    if not 'ARCH_FLAGS' in sys_env:
        sys_env['ARCH_FLAGS'] = '-arch i386 -arch x86_64'
    sys_env['CPPFLAGS'] = ('-I{0}/include '
                           '-I{0}/freetype2/include').format(bld_path)
    sys_env['CFLAGS'] = sys_env['ARCH_FLAGS']
    sys_env['LDFLAGS'] = '{0} -L{1}/lib'.format(
        sys_env['ARCH_FLAGS'],
        bld_path)
    sys_env['PATH'] = '{0}/bin:'.format(bld_path) + sys_env['PATH']
    ctx.env.env = sys_env


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
        val['dirnode'] = dirnode
        tarflag = 'j' if tarname.endswith('bz2') else 'z'
        ctx(
            rule = 'cp ${SRC} ${TGT}',
            source = srcnode,
            target = tarname,
        )
        ctx(
            rule = 'tar {0}xvf ${{SRC}}'.format(tarflag),
            source = tarname,
            target = dirnode
        )
    ctx( # zlib
        rule   = ('cd ${SRC} && '
                  './configure --prefix=${BLD_PREFIX} && '
                  'make -j3 install && '
                  'cd .. && ${TOUCH} ${TGT}'),
        source = EXTLIBS_PROC['zlib']['dirnode'],
        target = 'zlib.stamp',
    )
    ctx( # png
        rule   = ('cd ${SRC[0]} && '
                  './configure --disable-dependency-tracking '
                  '--prefix=${BLD_PREFIX} && '
                  'make -j3 install && '
                  'cd .. && ${TOUCH} ${TGT}'),
        source = [EXTLIBS_PROC['png']['dirnode'], 'zlib.stamp'],
        target = 'png.stamp',
    )
    ctx( # freetype
        rule   = ('cd ${SRC[0]} && '
                  './configure --prefix=${BLD_PREFIX} && '
                  'make -j3 && '
                  'make -j3 install && '
                  'cp objs/.libs/libfreetype.a . && '
                  'cd .. && ${TOUCH} ${TGT}'),
        source = [EXTLIBS_PROC['freetype']['dirnode'],
                  'zlib.stamp',
                  'png.stamp'],
        target = 'freetype.stamp',
    )
    lib_stamps = [s + '.stamp' for s in EXTLIBS_PROC]
    ctx( # Clean dynamic libraries just in case
        rule = 'rm -rf lib/*.dylib',
        source = lib_stamps)
