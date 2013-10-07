#######################
sketch of build process
#######################

Builds for minimum OSX version 10.6

From build file::

    MACOSX_DEPLOYMENT_TARGET=10.6
    OSX_SDK_VER=10.6

Architectures - all::

    ARCH_FLAGS=-ppc -arch i386 -arch x86_64

Build against specified library versions. ``make.osx`` versions::

    ZLIBVERSION=1.2.5
    PNGVERSION=1.5.4
    FREETYPEVERSION=2.4.6

Where current versions at time or writing (7 October 2013) are::

    ZLIBVERSION=1.2.8
    PNGVERSION=1.6.6
    FREETYPEVERSION=2.5.0.1

Build into some specified directory.

Compiler for Python 2.6 may need to be set to ``gcc-4.0`` (available in XCode
3.2.6, at least). I checked the version on my building machine with
``/Developer/usr/bin/xcodebuild -version``.

Build may or may not need to be on an OSX 10.6 machine.  Or some other version.

****
Plan
****

* for each library in ('zlib', 'png', 'freetype2'):
     download library
     configure with PREFIX
     make
     make install

* for each python in ('2.6', '2.7', '3.3'):
     with PREFIX
     python setup.py bdist_mpkg
     fix or add dependencies in ('six', 'dateutil', 'tornado', 'pyparsing')
     install (delete mpl and all dependencies) (install with all dependencies)
     test (test all dependencies, test matplotlib)
     install on clean machine (collect binary installer, install Python, Numpy,
     matplotlib)
     test on clean machine (test all dependencies, test matplotlib)

Libraries
=========

* library has URL and build recipe
* download -> configure -> make -> make install

**************
Implementation
**************

My current plan is to use `waf
<http://docs.waf.googlecode.com/git/book_17/single.html>`_

Each Python build will be a *variant build* as in
http://docs.waf.googlecode.com/git/book_17/single.html#_custom_build_outputs
