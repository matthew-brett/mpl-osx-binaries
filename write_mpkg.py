#!/usr/bin/env python
""" Copy the mpkg archive from the build directory to another directory

Probably run (from waf root directory) with::

    sudo python2.7 write_mpkg.py ~/Downloads

Where `python2.7` is the python you just built with
"""
# Will likely need sudo

import os
from os.path import join as pjoin, abspath, split as psplit, expanduser
import sys
from glob import glob
from subprocess import check_call
import shutil

BUILD_SDIR = 'build'

def _lib_path(start_path):
    version = sys.version_info
    return '{0}/lib/python{1}.{2}/site-packages'.format(
        start_path, version[0], version[1])


def main():
    try:
        out_path = sys.argv[1]
    except IndexError:
        raise ValueError("Need output directory as input")
    out_path = abspath(expanduser(out_path))
    # Check for built mpkgs
    build_path = pjoin(abspath(os.getcwd()), BUILD_SDIR)
    globber = pjoin(build_path, '*mpkg')
    mpkgs = glob(globber)
    if len(mpkgs) == 0:
        print("No mpkgs found with " + globber)
        sys.exit(1)
    # Put built version of bdist_mpkg onto the path
    env = os.environ
    env['PATH'] = pjoin(build_path, 'bin') + ':' + env['PATH']
    env['PYTHONPATH'] = _lib_path(build_path) + ':' + env['PYTHONPATH']
    # Write mpkgs with permissions updated
    for mpkg in mpkgs:
        _, mpkg_dir = psplit(mpkg)
        out_mpkg = pjoin(out_path, mpkg_dir)
        shutil.rmtree(out_mpkg, ignore_errors=True)
        shutil.copytree(mpkg, out_mpkg)
        check_call(['reown_mpkg', out_mpkg, 'root', 'admin'])


if __name__ == '__main__':
    main()
