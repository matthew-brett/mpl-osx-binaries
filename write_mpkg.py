#!/usr/bin/env python
# Copy the mpkg archive somewhere
# Will likely need sudo

from os.path import join as pjoin, abspath, split as psplit, expanduser
import sys
from glob import glob
from subprocess import check_call
import shutil

def main():
    try:
        out_path = sys.argv[1]
    except IndexError:
        raise ValueError("Need output directory as input")
    out_path = abspath(expanduser(out_path))
    globber = pjoin('build', '*mpkg')
    mpkgs = glob(globber)
    if len(mpkgs) == 0:
        print("No mpkgs found with " + globber)
        sys.exit(1)
    for mpkg in mpkgs:
        _, mpkg_dir = psplit(mpkg)
        out_mpkg = pjoin(out_path, mpkg_dir)
        shutil.rmtree(out_mpkg, ignore_errors=True)
        shutil.copytree(mpkg, out_mpkg)
        check_call(['reown_mpkg', out_mpkg, 'root', 'admin'])


if __name__ == '__main__':
    main()
