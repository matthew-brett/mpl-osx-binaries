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
  minimum version for matplotlib.  At time of writing (v1.3.1) this was numpy
  1.5

Run with::

    python2.7 waf distclean configure build

where ``python2.7`` is the python you want to build with.

The first time you run ``configure`` it will initalize the submodules, so you
might need to wait a few minutes.  Or run it yourself beforehand with::

    git submodule update --init

When the build is done, you should have a new ``matplotlib*mpkg`` directory in
``build``.  Copy it somewhere and set permissions with something like::

    sudo ./waf write_mpkg --mpkg-outpath=~/Downloads --mpkg-clobber

*********************
Updating dependencies
*********************

Some dependencies are archives, others are git submodule commits (tags usually).

To update the archives, download into the ``archive`` directory and edit the
``wscript`` file to use the new archive filename.

For git submodule commits, update the commit reference in the ``wscript`` file,
then run ``waf refresh_submodules`` to pull in any necessary commits that you
don't yet have in the submodules.
