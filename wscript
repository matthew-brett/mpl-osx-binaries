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
EXTLIBS = dict(
    zlib = 'v1.2.8',
    libpng = 'v1.5.9',
    freetype2 = 'VER-2-5-0-1',
)

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
    ctx.find_program('git', var='GIT')
    # Update submodules in repo
    ctx.exec_command('git submodule update --init')
    # Prepare environment variables for compilation
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


def build(ctx):
    src_node = ctx.path.get_src()
    src_path = src_node.abspath()
    bld_node = ctx.path.get_bld()
    bld_path = bld_node.abspath()
    lib_targets = {}
    for name, tag in EXTLIBS.items():
        git_dir = pjoin(src_path, name)
        prefix = pjoin('src', name)
        dirnode = bld_node.make_node(prefix)
        ctx(
            rule = ('cd {0} && '
                    'git archive --prefix={1}/ {2} | '
                    '( cd {3} && tar x )'.format(
                    git_dir, prefix, tag, bld_path)),
            target = dirnode,
        )
        patch_file = pjoin(src_path, 'patches', name, tag + '.patch')
        if os.path.isfile(patch_file):
            target = name + '.patch.stamp'
            ctx(
                rule = ('cd ${SRC} && patch -p1 < %s && '
                        'cd ../.. && ${TOUCH} ${TGT}' %
                        patch_file),
                source = dirnode,
                target = target,
            )
        else:
            target = dirnode
        lib_targets[name] = target
    ctx( # zlib
        rule   = ('cd src/zlib && '
                  './configure --prefix=${BLD_PREFIX} && '
                  'make -j3 install && '
                  'cd ../.. && ${TOUCH} ${TGT}'),
        source = lib_targets['zlib'],
        target = 'zlib.stamp',
    )
    ctx( # libpng
        rule   = ('cd src/libpng && '
                  './configure --disable-dependency-tracking '
                  '--prefix=${BLD_PREFIX} && '
                  'make -j3 install && '
                  'cd ../.. && ${TOUCH} ${TGT}'),
        source = [lib_targets['libpng'], 'zlib.stamp'],
        target = 'libpng.stamp',
    )
    ctx( # freetype
        rule   = ('cd src/freetype2 && '
                  './configure --prefix=${BLD_PREFIX} && '
                  'make -j3 && '
                  'make -j3 install && '
                  'cp objs/.libs/libfreetype.a . && '
                  'cd ../.. && ${TOUCH} ${TGT}'),
        source = [lib_targets['freetype2'],
                  'zlib.stamp',
                  'libpng.stamp'],
        target = 'freetype2.stamp',
    )
    lib_stamps = [s + '.stamp' for s in EXTLIBS]
    ctx( # Clean dynamic libraries just in case
        rule = 'rm -rf lib/*.dylib',
        source = lib_stamps)
