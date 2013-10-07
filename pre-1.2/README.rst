#######################################
OSX build method prior to version 1.2.0
#######################################

From version 1.0.0 to through version 1.1.1, matplotlib had a file ``make.osx``.

As you can see from this file, the Makefile has targets to download, build and
install versions of ``zlib, png, freetype2``.  There are other targets to build
matplotlib against these local builds.

``git log -- make.osx`` shows that this file got removed in October 2012 on the
basis that OSX already has these dependencies.

At least in my experience (MB), this is not always so, at least with the bare
machines that I tried on.

This is the last version of the file before it got removed, as a basis for a new
build system.

It comes from the output of ``git show
b7d49ff7c68a012e5f20e1f5c1bdb22b8c01368c:make.osx`` in the matplotlib tree.

I also fetched the then-current version of ``README.osx`` using the same method.
