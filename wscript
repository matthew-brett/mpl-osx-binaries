# waf script
# vim: ft=python
import os
from os.path import join as pjoin, abspath, split as psplit
import sys
from glob import glob

PY3 = sys.version_info[0] >= 3
if not PY3:
    from urllib import urlretrieve
    from urlparse import urlparse
else: # Python 3
    from urllib.request import urlretrieve
    from urllib.parse import urlparse


# External libraries
EXTLIBS = (
    ('bzip2', 'archives/bzip2-1.0.6.tar.gz'),
    ('zlib', 'v1.2.8'),
    ('libpng', 'v1.5.9'),
    ('freetype2', 'VER-2-5-0-1'))

PDU_PKG = ('archives/python-dateutil-2.0.tar.gz' if PY3
          else 'archives/python-dateutil-1.5.tar.gz')

PYPKGS = (
    ('setuptools',  'archives/setuptools-1.1.6.tar.gz'),
    ('bdist_mpkg', 'v0.5.0'),
    ('python-dateutil',  PDU_PKG),
    ('pytz', 'archives/pytz-2013.7.tar.gz'),
    ('six',  'archives/six-1.4.1.tar.gz'),
    ('pyparsing',  'archives/pyparsing-2.0.1.tar.gz'),
    ('tornado',  'v3.1.1')
)

# Packages for which we make an mpkg
MPKG_PKGS = ['tornado', 'pyparsing', 'python-dateutil', 'pytz', 'six']

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
    try:
        ctx.find_program('pkg-config')
    except ctx.errors.ConfigurationError:
        ctx.to_log('Failed to find pkg-config; consider installing from '
                   'source at http://pkgconfig.freedesktop.org/releases.')
        ctx.to_log('I used ``./configure --with-internal-glib && make '
                   '&& sudo make install``')
        ctx.fatal('Could not find pkg-config; see log for suggestion')
    # Update submodules in repo
    ctx.exec_command('git submodule update --init')
    # Prepare environment variables for compilation
    if not 'ARCH_FLAGS' in sys_env:
        sys_env['ARCH_FLAGS'] = '-arch i386 -arch x86_64'
    ctx.env.THIN_LDFLAGS = '{0} -L{1}/lib'.format(
        sys_env['ARCH_FLAGS'],
        bld_path)
    ctx.env.THICK_LDFLAGS = ctx.env.THIN_LDFLAGS + ' -lpng -lbz2'
    # For installing python modules
    ctx.env.PYTHONPATH = _lib_path(bld_path)
    sys_env['PYTHONPATH'] = ctx.env.PYTHONPATH
    sys_env['PKG_CONFIG_PATH'] = '{0}/lib/pkgconfig'.format(bld_path)
    sys_env['MACOSX_DEPLOYMENT_TARGET']='10.6'
    sys_env['CPPFLAGS'] = ('-I{0}/include '
                           '-I{0}/freetype2/include').format(bld_path)
    sys_env['CFLAGS'] = sys_env['ARCH_FLAGS']
    sys_env['LDFLAGS'] = ctx.env.THICK_LDFLAGS
    sys_env['PATH'] = '{0}/bin:'.format(bld_path) + sys_env['PATH']
    ctx.env.env = sys_env


def write_plist(work_dir, pkg_name, pkg_ver, component_sdir='Contents/Packages'):
    # Write plist starting at working directory
    from bdist_mpkg.plists import mpkg_info, write, python_requirement
    from bdist_mpkg import tools
    wd = abspath(work_dir)
    package_names = glob(pjoin(work_dir, component_sdir, '*.pkg'))
    package_names = [psplit(pn)[1] for pn in package_names]
    n_pkgs = len(package_names)
    extra_plist = dict(
            IFRequirementDicts=[python_requirement(pkg_name)],
            IFPkgFlagComponentDirectory=tools.unicode_path(
                './' + component_sdir))
    plist = mpkg_info(pkg_name, pkg_ver,
                      zip(package_names, ('selected',) * n_pkgs))
    plist.update(extra_plist)
    write(plist, pjoin(wd, 'Contents', 'Info.plist'))


def build(ctx):
    src_node = ctx.path.get_src()
    src_path = src_node.abspath()
    bld_node = ctx.path.get_bld()
    bld_path = bld_node.abspath()
    lib_targets = {}
    lib_dirnames = {}
    for name, source in EXTLIBS:
        if source.startswith('archives/'):
            _, pkg_file = psplit(source)
            assert pkg_file.endswith('.tar.gz')
            pkg_dir, _ = pkg_file.split('.tar.', 1)
            pkg_ver, _ = pkg_dir.split('-', 1)
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
            pkg_ver = source
            ctx(
                rule = ('cd {0} && '
                        'git archive --prefix={1}/ {2} | '
                        '( cd {3} && tar x )'.format(
                        git_dir, prefix, source, bld_path)),
                target = dirnode,
            )
        patch_file = pjoin(src_path, 'patches', name, pkg_ver + '.patch')
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
        lib_dirnames[name] = prefix
    ctx( # bzip2
        rule   = ('cd %s && '
                  'LDFLAGS="${THIN_LDFLAGS}" make -j3 && '
                  'LDFLAGS="${THIN_LDFLAGS}" make install PREFIX=${BLD_PREFIX} && '
                  'cd ../.. && ${TOUCH} ${TGT}' %
                 lib_dirnames['bzip2']),
        source = lib_targets['bzip2'],
        target = 'bzip2.stamp',
    )
    ctx( # zlib
        rule   = ('cd src/zlib && '
                  'LDFLAGS="${THIN_LDFLAGS}" ./configure --prefix=${BLD_PREFIX} && '
                  'LDFLAGS="${THIN_LDFLAGS}" make -j3 install && '
                  'cd ../.. && ${TOUCH} ${TGT}'),
        source = lib_targets['zlib'],
        target = 'zlib.stamp',
    )
    ctx( # libpng
        rule   = ('cd src/libpng && '
                  'LDFLAGS="${THIN_LDFLAGS}" ./configure --disable-dependency-tracking '
                  '--prefix=${BLD_PREFIX} && '
                  'LDFLAGS="${THIN_LDFLAGS}" make -j3 install && '
                  'cd ../.. && ${TOUCH} ${TGT}'),
        source = [lib_targets['libpng'], 'zlib.stamp'],
        target = 'libpng.stamp',
    )
    ctx( # freetype
        rule   = ('cd src/freetype2 && '
                  './configure --prefix=${BLD_PREFIX} && '
                  'make -j3 && '
                  'make -j3 install && '
                  'cd ../.. && ${TOUCH} ${TGT}'),
        source = [lib_targets['freetype2'],
                  'bzip2.stamp',
                  'zlib.stamp',
                  'libpng.stamp'],
        target = 'freetype2.stamp',
    )
    lib_stamps = [s[0] + '.stamp' for s in EXTLIBS]
    ctx( # Clean dynamic libraries just in case
        rule = 'rm -rf lib/*.dylib && ${TOUCH} ${TGT}',
        source = lib_stamps,
        target = 'dylib_deleted.stamp')
    # Install python build dependencies
    my_stamps = ['dylib_deleted.stamp']
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
            _, pkg_file = psplit(source)
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
    # Write setup.cfg into tree
    def write_cfg(task):
        print("Here " + os.getcwd())
        fname = task.outputs[0].abspath()
        with open(fname, 'wt') as fobj:
            fobj.write("""
# setup.cfg file
[directories]
# 0verride the default basedir in setupext.py.
# This can be a single directory or a comma-delimited list of directories.
basedirlist = {0}, /usr
""".format(bld_path))
    setup_cfg_fname = pjoin(prefix, 'setup.cfg')
    ctx(
        rule = write_cfg,
        source = dirnode,
        target = [setup_cfg_fname]
    )
    # Compile mpl
    stamp_file = my_name + '.stamp'
    ctx(
        rule = ('cd %s && ${PYTHON} setup.py bdist_mpkg && '
                'cd ../.. && ${TOUCH} %s' % (prefix, stamp_file)
                ),
        source = [setup_cfg_fname] + my_stamps,
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
    def update_plist(task):
        mpkgs = glob('{0}/{1}*.mpkg'.format(bld_path, my_name))
        assert len(mpkgs) == 1
        write_plist(mpkgs[0], my_name, my_tag)
        fname = task.outputs[0].abspath()
        with open(fname, 'wt') as fobj:
            fobj.write('done')

    ctx(rule = update_plist,
        source = 'mpkg.stamp',
        target = 'mpkg_plist.stamp'
       )
    # Change the permissions with something like
    # sudo write_mpkg.py from repo directory
