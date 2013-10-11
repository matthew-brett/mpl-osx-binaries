# waf script # vim: ft=python
import os
from os.path import join as pjoin
import sys

PY3 = sys.version_info[0] >= 3
if not PY3:
    from urllib import urlretrieve
    from urlparse import urlparse
else: # Python 3
    from urllib.request import urlretrieve
    from urllib.parse import urlparse


# External libraries
EXTLIBS = dict(
    zlib = 'v1.2.8',
    libpng = 'v1.5.9',
    freetype2 = 'VER-2-5-0-1')

PYPKGS = {
    'bdist_mpkg': 'v0.5.0',
    'setuptools':  'archives/setuptools-1.1.6.tar.gz',
    'tornado':  'v3.1.1',
    'pyparsing':  'archives/pyparsing-2.0.1.tar.gz',
    'python-dateutil':  'archives/python-dateutil-1.5.tar.gz',
    'six':  'archives/six-1.4.1.tar.gz'}

if PY3:
    PYPKGS['python-dateutil'] = 'archives/python-dateutil-2.0.tar.gz'

MPKG_PKGS = ['tornado', 'pyparsing', 'python-dateutil', 'six']

MYSELF = ('matplotlib', '1.3.1')


def options(opt):
    opt.load('compiler_c')
    # Copy of python.py extension from waf
    opt.load('mypython')


def _lib_path(start_path):
    version = sys.version_info
    return '{0}/lib/python{1}.{2}/site-packages'.format(
        start_path, version[0], version[1])


def configure(ctx):
    sys_env = dict(os.environ)
    bld_path = ctx.path.get_bld().abspath()
    ctx.load('compiler_c')
    ctx.load('mypython')
    ctx.check_python_headers()
    ctx.check_python_module('numpy')
    ctx.env.BLD_PREFIX = bld_path
    ctx.find_program('touch', var='TOUCH')
    ctx.find_program('git', var='GIT')
    # Update submodules in repo
    ctx.exec_command('git submodule update --init')
    # Prepare environment variables for compilation
    # For installing python modules
    ctx.env.PYTHONPATH = _lib_path(bld_path)
    sys_env['PYTHONPATH'] = ctx.env.PYTHONPATH
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
    # Install python build dependencies
    my_stamps = lib_stamps[:]
    mpkg_stamps = [] # mpkgs we are going to add
    # We need a node to refer to this as-yet non-existent file
    site_pkgs = ctx.env.PYTHONPATH
    site_pkgs_node = bld_node.make_node(site_pkgs)
    setuptools_stamp = bld_node.make_node('setuptools.stamp')
    # We need the install directory first
    ctx(
        rule = 'mkdir -p ' + ctx.env.env['PYTHONPATH'],
        target = site_pkgs_node
    )
    # And the mpkg framework
    for name in PYPKGS:
        source = PYPKGS[name]
        depends = [site_pkgs_node]
        if name != 'setuptools':
            depends.append(setuptools_stamp)
        if source.startswith('archives/'):
            _, pkg_file = os.path.split(source)
            assert pkg_file.endswith('.tar.gz')
            pkg_dir, _ = pkg_file.split('.tar.', 1)
            dirnode = bld_node.make_node('src/' + pkg_dir)
            pkg_path = pjoin(src_path, source)
            ctx(
                rule = ('cd src && tar zxvf ' + pkg_path),
                target = dirnode)
        else: # assume tag
            git_dir = pjoin(src_path, name)
            prefix = pjoin('src', name)
            dirnode = bld_node.make_node(prefix)
            ctx(
                rule = ('cd {0} && '
                        'git archive --prefix={1}/ {2} | '
                        '( cd {3} && tar x )'.format(
                        git_dir, prefix, source, bld_path)),
                target = dirnode,
            )
        # Install
        stamp_file = name + '.stamp'
        ctx(
            rule = ('cd ${SRC} && ${PYTHON} setup.py install '
                    '--prefix=${BLD_PREFIX} && '
                    'cd ../.. && ${TOUCH} ' + stamp_file
                   ),
            source = [dirnode] + depends,
            target = stamp_file)
        my_stamps.append(stamp_file)
        # If mpkg needed, make that
        if name in MPKG_PKGS:
            mpkg_stamp_file = name + '.mpkg.stamp'
            ctx(
                rule = ('cd %s && ${PYTHON} setup.py bdist_mpkg && '
                        'cd ../.. && ${TOUCH} %s' %
                        (prefix, mpkg_stamp_file)
                    ),
                source = stamp_file,
                target = mpkg_stamp_file)
            mpkg_stamps.append(mpkg_stamp_file)
    # At last the real package
    my_name, my_tag = MYSELF
    git_dir = pjoin(src_path, my_name)
    prefix = pjoin('src', my_name)
    dirnode = bld_node.make_node(prefix)
    ctx(
        rule = ('cd {0} && '
                'git archive --prefix={1}/ {2} | '
                '( cd {3} && tar x )'.format(
                git_dir, prefix, my_tag, bld_path)),
        target = dirnode,
    )
    stamp_file = my_name + '.stamp'
    ctx(
        rule = ('cd %s && ${PYTHON} setup.py bdist_mpkg && '
                'cd ../.. && ${TOUCH} %s' % (prefix, stamp_file)
                ),
        source = [dirnode] + my_stamps,
        target = stamp_file)
    # Now the mpkg
    """
    def compile_mpkg(task):
        # Now all the mpkgs are built, compile them
        my_mpkgs = os.listdir()
    ctx(
        rule = compile_mpkg,
        source = [stamp_file] + mpkg_stamps,
        target = 'mpkg.stamp')
    """

