# waf script
# vim: ft=python
from __future__ import division, print_function, absolute_import
import os
from os.path import join as pjoin, abspath, split as psplit, isfile
import sys
from glob import glob
import shutil

PY3 = sys.version_info[0] >= 3

from wafutils import back_tick, FilePackageMaker as FPM, GitPackageMaker as GPM

# External libraries
bzip2_pkg = FPM('bzip2',
                'archives/bzip2-1.0.6.tar.gz',
                ('cd ${SRC[0].abspath()} && '
                 'LDFLAGS="${THIN_LDFLAGS}" make -j3 && '
                 'make install PREFIX=${BLD_PREFIX}'))
zlib_pkg = GPM('zlib',
               'v1.2.8',
               ('cd ${SRC[0].abspath()} && '
                'LDFLAGS="${THIN_LDFLAGS}" ./configure --prefix=${BLD_PREFIX} && '
                'make -j3 install'))
libpng_pkg = GPM('libpng',
                 'v1.5.9',
                 ('cd ${SRC[0].abspath()} && '
                  'LDFLAGS="${THIN_LDFLAGS}" ./configure --disable-dependency-tracking '
                  '--prefix=${BLD_PREFIX} && '
                  'make -j3 install'),
                 after = 'zlib.build')
freetype2_pkg = GPM('freetype2',
                    'VER-2-5-0-1',
                    ('cd ${SRC[0].abspath()} && '
                     './configure --prefix=${BLD_PREFIX} && '
                     'make -j3 && ' # make and install have to be separate
                     'make -j3 install'), # I have no idea why
                    patcher = 'patches/freetype2/VER-2-5-0-1.patch',
                    after = ['bzip2.build', 'libpng.build'])

EXT_LIBS = [bzip2_pkg, zlib_pkg, libpng_pkg, freetype2_pkg]

python_install_rule = ('cd ${SRC[0].abspath()} && ${PYTHON} setup.py install '
                       '--prefix=${BLD_PREFIX}')
mpkg_build_rule = ('cd ${SRC[0].abspath()} && bdist_mpkg setup.py bdist_mpkg')


# Python packages have to build sequentially because they may compete writing
# easy-install.pth when installing
setuptools_pkg = FPM('setuptools',
                     'archives/setuptools-1.1.6.tar.gz',
                     python_install_rule,
                     after = ['freetype2.build'])
bdist_mpkg_pkg = GPM('bdist_mpkg',
                     'v0.5.0',
                     python_install_rule,
                     after = ['setuptools.build'])
python_dateutil_pkg = FPM('python-dateutil',
                          'archives/python-dateutil-2.0.tar.gz' if PY3
                          else 'archives/python-dateutil-1.5.tar.gz',
                          python_install_rule,
                          after = ['bdist_mpkg.build'])
pytz_pkg = FPM('pytz',
               'archives/pytz-2013.7.tar.gz',
               python_install_rule,
               after = ['python-dateutil.build'])
six_pkg = FPM('six',
              'archives/six-1.4.1.tar.gz',
              python_install_rule,
              after = ['pytz.build'])
pyparsing_pkg = FPM('pyparsing',
                    'archives/pyparsing-2.0.1.tar.gz',
                    python_install_rule,
                    after = ['six.build'])
tornado_pkg = GPM('tornado',
                  'v3.1.1',
                  python_install_rule,
                  after = ['pyparsing.build'])

def _write_setup_cfg(task):
    setup_node = task.inputs[0].make_node('setup.cfg')
    setup_node.write("""
# setup.cfg file
[directories]
# 0verride the default basedir in setupext.py.
# This can be a single directory or a comma-delimited list of directories.
basedirlist = {0}, /usr
""".format(task.env.BLD_PREFIX))

matplotlib_pkg = GPM('matplotlib',
                     '1.3.1',
                     mpkg_build_rule,
                     patcher = _write_setup_cfg,
                     after = ['tornado.build', 'de-dylibbed'])

# Python packages
PY_PKGS = [setuptools_pkg, bdist_mpkg_pkg, python_dateutil_pkg, pytz_pkg,
           six_pkg, pyparsing_pkg, tornado_pkg, matplotlib_pkg]

# Packages for which we make an mpkg
MPKG_PKGS = [python_dateutil_pkg, pytz_pkg, six_pkg, pyparsing_pkg, tornado_pkg]

MPKG_META_PKG = matplotlib_pkg


def options(opt):
    opt.load('compiler_c')
    # Copy of python.py extension from waf
    opt.load('mypython')
    # Output for mpkg writing
    opt.add_option('--mpkg-outpath', action='store',
                   help='directory to write built mpkg')
    opt.add_option('--mpkg-clobber', action='store_true', default=False,
                   help='whether to overwrite existing output mpkg')


def _lib_path(start_path):
    version = sys.version_info
    return '{0}/lib/python{1}.{2}/site-packages'.format(
        start_path, version[0], version[1])


def configure(ctx):
    sys_env = dict(os.environ)
    bld_path = ctx.bldnode.abspath()
    ctx.load('compiler_c')
    ctx.load('mypython')
    ctx.check_python_headers()
    ctx.check_python_module('numpy')
    ctx.env.BLD_PREFIX = bld_path
    ctx.env.BLD_SRC = pjoin(bld_path, 'src')
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
    print('Running git submodule update, this might take a while')
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
    # Get newly install bdist_mpkg onto the path
    import pkg_resources
    pkg_resources.require('bdist_mpkg')
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
    bld_node = ctx.bldnode
    bld_path = bld_node.abspath()
    # We need the src directory before we start
    def pre(ctx):
        # src directory for code tree copies
        ctx.exec_command('mkdir -p {0}/src'.format(bld_path))
        # python site-packages directory for python installs
        ctx.exec_command('mkdir -p {0}'.format(_lib_path(bld_path)))
    ctx.add_pre_fun(pre)
    # Build the external libs
    for pkg in EXT_LIBS:
        pkg.unpack_patch_build(ctx)
    ctx( # Clean dynamic libraries just in case
        rule = 'rm -rf lib/*.dylib',
        after = 'freetype2.build',
        name = 'de-dylibbed')
    # Install python build dependencies
    mpkg_tasks = []
    for pkg in PY_PKGS:
        py_task_name, dir_node = pkg.unpack_patch_build(ctx)
        # Run the mpkgs after the bdist_mpkg install, and the package install
        if pkg in MPKG_PKGS:
            mpkg_task = pkg.name + '.mpkg.build'
            ctx(
                rule = mpkg_build_rule,
                source = [dir_node],
                after = [py_task_name, 'bdist_mpkg.build'],
                name = mpkg_task)
            mpkg_tasks.append(mpkg_task)
    # Now the mpkg
    meta_name = MPKG_META_PKG.name
    ctx(
        rule = ('cp -r src/{0}/dist/*.mpkg . && '
                'cp -r src/*/dist/*.mpkg/Contents/Packages/* '
                '{0}*.mpkg/Contents/Packages').format(meta_name),
        after = ['matplotlib.build'] + mpkg_tasks,
        name = 'mpkg.build')
    ctx(rule =
        '{python} rewrite_plist.py '
        '{meta_name} {bld_path}/{meta_name}*.mpkg'.format(
            python=ctx.env.PYTHON, meta_name=meta_name, bld_path=bld_path),
        after = ['mpkg.build'],
       )


def write_mpkg(ctx):
    # Change the permissions for mpkg and copy file somewhere
    mpkg_outpath = ctx.options.mpkg_outpath
    if mpkg_outpath is None:
        ctx.fatal('Need to set --mpkg-outpath to write mpkgs')
    # Need to be sudo
    if not back_tick('whoami') == 'root':
        ctx.fatal('Need to be root to run dist command - use `sudo ./waf write_mpkg`?')
    # Get build time configuration
    from waflib.ConfigSet import ConfigSet
    env = ConfigSet()
    env_cache = pjoin('build', 'c4che', '_cache.py')
    if not isfile(env_cache):
        ctx.fatal('Run `configure` and `build` before `dist`')
    env.load(env_cache)
    # Check if any mpkgs have been built
    build_path = env.BLD_PREFIX
    globber = pjoin(build_path, '*mpkg')
    mpkgs = glob(globber)
    if len(mpkgs) == 0:
        ctx.fatal("No mpkgs found with " + globber)
    # Put built version of bdist_mpkg onto the path
    os.environ['PATH'] = pjoin(build_path, 'bin') + ':' + os.environ['PATH']
    os.environ['PYTHONPATH'] = env['PYTHONPATH']
    # Write mpkgs with permissions updated
    for mpkg in mpkgs:
        _, mpkg_dir = psplit(mpkg)
        out_mpkg = pjoin(mpkg_outpath, mpkg_dir)
        print('Found {0}, writing {1}'.format(mpkg, out_mpkg))
        if os.path.exists(out_mpkg):
            if not ctx.options.mpkg_clobber:
                ctx.fatal('mpkg exists, --mpkg-clobber not set')
            shutil.rmtree(out_mpkg, ignore_errors=True)
        shutil.copytree(mpkg, out_mpkg)
        ctx.exec_command(['reown_mpkg', out_mpkg, 'root', 'admin'])
