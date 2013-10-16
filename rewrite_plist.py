#!/usr/bin/env python
""" Script to rewrite plist file in mpkg directory

Analyzes an mpkg directory for added pkg sub-packages, and fills the mpkg
plist.info accordingly.
"""
import sys
from os.path import abspath, join as pjoin, split as psplit
from optparse import OptionParser
from glob import glob
from bdist_mpkg.plists import mpkg_info, write, python_requirement
from bdist_mpkg import tools

COMPONENT_DIRECTORY = 'Contents/Packages'

def main():
    parser = OptionParser(usage=
                          'usage: %prog [options] <package_name> <mpkg_root>')
    parser.add_option("--component-directory",
                      action = 'store',
                      default = COMPONENT_DIRECTORY,
                      dest="comp_dir",
                      help="Subdirectory containing package directories; "
                      "defaults to " + COMPONENT_DIRECTORY)
    options, args = parser.parse_args()
    if len(args) != 2:
        parser.print_help()
        sys.exit(1)
    pkg_name, wd = args
    wd = abspath(wd)
    package_names = glob(pjoin(wd, COMPONENT_DIRECTORY, '*.pkg'))
    package_names = [psplit(pn)[1] for pn in package_names]
    n_pkgs = len(package_names)
    extra_plist = dict(
            IFRequirementDicts=[python_requirement(pkg_name)],
            IFPkgFlagComponentDirectory=tools.unicode_path(
                './' + COMPONENT_DIRECTORY))
    plist = mpkg_info(pkg_name, '1.7',
                      zip(package_names, ('selected',) * n_pkgs))
    plist.update(extra_plist)
    write(plist, pjoin(wd, 'Contents', 'Info.plist'))


if __name__ == '__main__':
    main()
