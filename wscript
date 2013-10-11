# waf script
# vim: ft=python
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

PDU_PKG = ('archives/python-dateutil-2.0.tar.gz' if PY3
          else 'archives/python-dateutil-1.5.tar.gz')

PYPKGS = (
    ('setuptools',  'archives/setuptools-1.1.6.tar.gz'),
    ('bdist_mpkg', 'v0.5.0'),
    ('python-dateutil',  PDU_PKG),
    ('six',  'archives/six-1.4.1.tar.gz'),
    ('pyparsing',  'archives/pyparsing-2.0.1.tar.gz'),
    ('tornado',  'v3.1.1')
)

# Packages for which we make an mpkg
MPKG_PKGS = ['tornado', 'pyparsing', 'python-dateutil', 'six']

# The one we've been waiting for
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
    site_pkgs = _lib_path('.')
    site_pkgs_node = bld_node.make_node(site_pkgs)
    # We need the install directory first
    ctx(
        rule = 'mkdir -p ${TGT}',
        target = site_pkgs_node
    )
    # Run installs sequentially; nasty things happen when more than one package
    # is trying to write to easy-install.pth at the same time
    install_depends = [site_pkgs_node]
    mpkg_stamps = [] # mpkgs we are going to add
    for name, source in PYPKGS:
        # Copy source first; can be asynchronous
        if source.startswith('archives/'):
            _, pkg_file = os.path.split(source)
            assert pkg_file.endswith('.tar.gz')
            pkg_dir, _ = pkg_file.split('.tar.', 1)
            prefix = pjoin('src', pkg_dir)
            dirnode = bld_node.make_node(prefix)
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
        # Install must run in sequence to avoid several installs trying to write
        # the easy-install.pth file at the same time
        stamp_file = bld_node.make_node(name + '.stamp')
        ctx(
            rule = ('cd %s && ${PYTHON} setup.py install '
                    '--prefix=${BLD_PREFIX} && '
                    'cd ../.. && ${TOUCH} %s' %
                    (prefix, stamp_file)
                   ),
            source = [dirnode] + install_depends[:],
            target = stamp_file)
        my_stamps.append(stamp_file)
        install_depends = [stamp_file]
        # Run the mpkgs after the bdist_mpkg install, and the package install
        if name in MPKG_PKGS:
            mpkg_stamp_file = bld_node.make_node(name + '.mpkg.stamp')
            ctx(
                rule = ('cd %s && bdist_mpkg setup.py bdist_mpkg && '
                        'cd ../.. && ${TOUCH} %s' %
                        (prefix, mpkg_stamp_file)
                    ),
                source = [stamp_file, 'bdist_mpkg.stamp'],
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
    ctx(
        rule = ('cp -r src/{0}/dist/*.mpkg . && '
                'cp -r src/*/dist/*.mpkg/Contents/Packages/* '
                '{0}*.mpkg/Contents/Packages && '
                '${{TOUCH}} {1}').format(my_name, 'mpkg.stamp'),
        source = [stamp_file] + mpkg_stamps,
        target = 'mpkg.stamp')
    # Write the plist
    # See rewrite_plist.py
    # Change the permissions with something like
    # sudo reown_mpkg reginald.mpkg root admin
