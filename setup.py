import distutils.command.install as orig
import inspect
import sys

from setuptools import setup, find_packages
from setuptools.command.install import install as _install


class install(_install):
    def run(self):
        # Explicit request for old-style install?  Just do it
        if self.old_and_unmanageable or self.single_version_externally_managed:
            orig.install.run(self)

        self.install_pywin32()

        if not self._called_from_setup(inspect.currentframe()):
            # Run in backward-compatibility mode to support bdist_* commands.
            orig.install.run(self)
        else:
            self.do_egg_install()

    def install_pywin32(self):
        import subprocess

        pywin32_req = None
        for req in install_requires:
            if req.startswith("pywin32"):
                pywin32_req = req
                break

        if pywin32_req is not None:
            subprocess.run(["pip", "install", pywin32_req])


with open("README.md", "r") as file:
    long_description = file.read()


if sys.platform == "win32":
    install_requires = ["pywin32>=227"]
else:
    install_requires = ["pyudev>=0.21.0"]


setup(name="device_manager",
      version="0.1",
      author="Forschungszentrum Jülich GmbH - ZEA-2",
      description="A tool for searching and managing plug-and-play devices",
      long_description=long_description,
      long_description_content_type="text/markdown",
      cmdclass={"install": install},
      packages=find_packages(),
      python_requires=">=3.6",
      install_requires=install_requires,
      extras_require={"nmap": ["python-nmap>=0.6.1"]},
      classifiers=["Programming Language :: Python :: 3",
                   "License :: OSI Approved :: MIT License",
                   "Operating System :: OS Independent"],
      url="http://zea2git.zel.kfa-juelich.de/Quantencomputing/DeviceManager")
