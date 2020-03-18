#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup script for the device manager.

Authors:
    Lukas Lankes, Forschungszentrum Jülich GmbH - ZEA-2, l.lankes@fz-juelich.de
"""

import distutils.command.install as orig
import inspect
import os
import re
import subprocess
import sys

from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop

# Requirements
REQ_PYWIN32 = "pywin32>=227"
REQ_PYUDEV  = "pyudev>=0.21.0"
REQ_PYNMAP  = "python-nmap>=0.6.1"


def pip_install(package: str):
    """Installs a package manually with pip"""
    return subprocess.check_call(["pip", "install", package])


def extract_version(version_file_name):
    """Extracts the version from a python file.

    The statement setting the __version__ variable must not be indented. Comments after that
    statement are allowed.
    """
    regex = re.compile(r"^__version__\s*=\s*['\"]([^'\"]*)['\"]\s*(#.*)?$")
    with open(version_file_name, "r") as version_file:
        lines = version_file.read().splitlines()
    for line in reversed(lines):
        version_match = regex.match(line)
        if version_match:
            return version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string.")


class CustomInstall(install):
    """Custom installation class."""

    def run(self):
        """Run the installation"""
        # Explicit request for old-style install?  Just do it
        if self.old_and_unmanageable or self.single_version_externally_managed:
            return orig.install.run(self)

        if sys.platform == "win32":
            # Install pywin32 manually with pip
            pip_install(REQ_PYWIN32)

        if not self._called_from_setup(inspect.currentframe()):
            # Run in backward-compatibility mode to support bdist_* commands.
            orig.install.run(self)
        else:
            self.do_egg_install()


class CustomDevelop(develop):
    """Custom installation class for development mode."""

    def run(self):
        """Run the installation"""
        if not self.uninstall:
            if sys.platform == "win32":
                # Install pywin32 manually with pip
                pip_install(REQ_PYWIN32)

        return super().run()


def main():
    """Main-function which is called if this file is executed as script."""
    with open("README.md", "r") as file:
        long_description = file.read()

    if sys.platform == "win32":
        install_requires = [REQ_PYWIN32]
        op_system = "Operating System :: Microsoft :: Windows"
    elif sys.platform == "linux":
        install_requires = [REQ_PYUDEV]
        op_system = "Operating System :: POSIX :: Linux"
    else:
        raise OSError("The platform \"{}\" is not supported".format(sys.platform))

    version = extract_version(os.path.join("device_manager", "__init__.py"))

    return setup(name="device-manager",
                 packages=["device_manager", "device_manager.scanner"],
                 version=version,
                 author="Forschungszentrum Jülich GmbH - ZEA-2",
                 description="A tool for searching and managing plug-and-play devices",
                 long_description=long_description,
                 long_description_content_type="text/markdown",
                 cmdclass={"install": CustomInstall,
                           "develop": CustomDevelop},
                 python_requires=">=3.6",
                 install_requires=install_requires,
                 extras_require={"nmap": [REQ_PYNMAP]},
                 classifiers=["Programming Language :: Python :: 3.6",
                              "Programming Language :: Python :: 3.7",
                              "Programming Language :: Python :: 3.8",
                              "License :: OSI Approved :: MIT License",
                              op_system],
                 url="https://github.com/zea2/DeviceManager")


if __name__ == "__main__":
    # Call main-function if this file is executed as script
    main()
