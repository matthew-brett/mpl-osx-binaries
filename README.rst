#######################
Matplotlib OSX binaries
#######################

Build system for matplotlib OSX binaries

You'll need:

* OSX >=10.6 (I've tested 10.6 and 10.8, <10.6 might work, I haven't tested)
* Xcode command line tools
* git on your system path
* pkg-config on your system path.  I build this from source at
  http://pkgconfig.freedesktop.org/releases, using::

    ./configure --with-internal-glib
    make
    sudo make install
* Python.org python installed from the DMG installer. I've tested with Python
  2.7 and 3.3.  It might work with the system python, I haven't tried
* For each python you want to install from, a version of numpy >= the required
  minimum version for matplotlib.  At time of writing (matplotlib v1.3.1) this
  was numpy 1.5

Run with::

    python2.7 waf distclean configure build

where ``python2.7`` is the python you want to build with.

The first time you run ``configure`` it will initalize the submodules, so you
might need to wait a few minutes.  Or run it yourself beforehand with::

    git submodule update --init

When the build is done, you should have a new ``matplotlib*mpkg`` directory in
``build``.  Copy it somewhere and set permissions with something like::

    sudo ./waf write_mpkg --mpkg-outpath=~/Downloads --mpkg-clobber

You'll also have a `wheelhouse` directory in `build` with `.whl` files for
matplotlib and all its dependencies.

*********************
Updating dependencies
*********************

Some dependencies are archives, others are git submodule commits (tags usually).

To update the archives, download into the ``archive`` directory and edit the
``wscript`` file to use the new archive filename.

For git submodule commits, update the commit reference in the ``wscript`` file,
then run ``waf refresh_submodules`` to pull in any necessary commits that you
don't yet have in the submodules.

***************
Patching source
***************

You may need to patch the archive sources or the git tag.  You can do this by
defining a patch function to the archive / git building commands, or a patch
file to apply with `patch -p1 < thefile` from the archive / git source. The
filename is from the root directory (containing the `waf` binary and this
`README.rst`).  For example, this is the setup command for the freetype
library::

    freetype2_pkg = GPM('freetype2',
                        'VER-2-5-0-1',
                        ('cd ${SRC[0].abspath()} && '
                        './configure --prefix=${bld.bldnode.abspath()} && '
                        'make -j3 && ' # make and install have to be separate
                        'make -j3 install'), # I have no idea why
                        patcher = 'patches/freetype2/VER-2-5-0-1.patch',
                        after = ['bzip2.build', 'libpng.build'])

`GPM` is the Git Package Manager class, `VER-2-5-0-1` is the git tag, followed
by the build rule, followed by the patch file to apply. `GPM` code is in
`wafutils.py` in the root directory. `FPM` is the equivalent class for managing
file archives.

See `_write_setup_cfg` for an example of a patching callable, in this case for
the matplotlib build. The callable is a build rule in waf terms.
