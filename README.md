[![Build Status](https://travis-ci.com/zea2/DeviceManager.svg?branch=master)](https://travis-ci.com/zea2/DeviceManager)
[![Coverage Status](https://coveralls.io/repos/github/zea2/DeviceManager/badge.svg?branch=master)](https://coveralls.io/github/zea2/DeviceManager?branch=master)
[![Documentation Status](https://readthedocs.org/projects/devicemanager/badge/?version=latest)](https://devicemanager.readthedocs.io/en/latest/?badge=latest)

# DeviceManager

Python device manager for plug-and-play devices

## Installation

To install the DeviceManager, perform the following steps:

1. Clone this repository
```
git clone https://github.com/zea2/DeviceManager
```

2. Navigate to the cloned repository
```
cd DeviceManager
```

3. Install the project
   1. Use pip for installation
      ```
      pip install .
      ```
   2. Or use the setup script:
      ```
      python setup.py install
      ```
   - If you also want to install the **nmap**-functionality, use the following command, to install the DeviceManager.
     ```
     pip install .[nmap]
     ```
     To use the nmap-functionality the nmap-software is additionally required.
     - On Windows you need to download the software from https://nmap.org/download.html
     - On Linux it can be installed with `sudo apt-get install nmap`
   
   
   On linux you eventually need to use the commands `pip3` or `python3` instead of `pip` or `python`.

## Examples

Useful examples can be found at [docs/source/examples](docs/source/examples).
