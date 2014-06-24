# Source this script for travis install
# Support travis-ci testing.
#
# The idea and code ripped off with thanks and dmiration from :
# https://github.com/matplotlib/mpl_mac_testing

source terryfy/travis_tools.sh


function build_install_binaries {
    $PYTHON_CMD waf configure build -v
    mkdir build/packages
    sudo $PYTHON_CMD ./waf write_mpkg --mpkg-outpath=build/packages
    sudo installer -pkg build/packages/*.mpkg -target /
    require_success "Failed to build/install matplotlib"
}


# Install macpython without virtualenv (to allow mpkg install test)
get_python_environment macpython $VERSION

# Dependencies for building
brew install pkg-config

# Dependencies for testing
$PIP_CMD install nose

build_install_binaries
