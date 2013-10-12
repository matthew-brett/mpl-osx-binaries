#######################
Matplotlib OSX binaries
#######################

Build system for matplotlib OSX binaries

You'll need:

* OSX 10.6 (>10.6 might work, I haven't tested)
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

    python2.7 waf distclean
    python2.7 waf configure
    python2.7 waf build

where ``python2.7`` is the python you want to build with.

The first time you run ``configure`` it will initalized the submodules, so you
might need to wait a few minutes.  Or run it yourself beforehand with::

    git submodule update --init

When the build is done, you should have a new ``matplotlib*mpkg`` directory in
``build``.  Copy it somewhere and set permissions with something like::

    ./write_mpkg.py ~/Downloads
