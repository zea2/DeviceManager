[![Build Status](https://travis-ci.com/zea2/DeviceManager.svg?branch=master)](https://travis-ci.com/zea2/DeviceManager)
[![Coverage Status](https://coveralls.io/repos/github/zea2/DeviceManager/badge.svg?branch=master)](https://coveralls.io/github/zea2/DeviceManager?branch=master)
[![Documentation Status](https://readthedocs.org/projects/devicemanager/badge/?version=latest)](https://devicemanager.readthedocs.io/en/latest/?badge=latest)

# DeviceManager

Python device manager for plug-and-play devices. The DeviceManager allows you to search for
connected devices and you can store them into a dicitonary by a user-defined name. By this, you will
never have to guess the device's address again. The DeviceManager will search for updated addresses
automatically. So you will always know your device's address, even if it got a new address after it
was disconnected and reconnected. For this purpose, the DeviceManager is also serializable into a
JSON-file. So your devices are not only stored within the session but also beyond and you have the
ability to share your device dictionaries with your colleagues.

Currently supported device types are:

- USB devices
- Ethernet/LAN devices


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
   - To install the DeviceManager, you need to know if you want to use the *nmap*-functionality. If
     not, install the package like this:
     
     ```
     $ pip3 install .
     ```

   - If you want to use *nmap* to get better results when searching for network devices, use this:

     ```
     $ pip3 install .[nmap]
     ```
     
     To use the *nmap*-functionality the *nmap*-software is required additionally:
     
     - On Windows you will need to download the software from https://nmap.org/download.html
     - On Linux *nmap* can be installed with `sudo apt-get install nmap`
   
   
   On linux you eventually need to use the commands `pip3` or `python3` instead of `pip` or
   `python`.

## Documentation

You can find a documentation on how to setup and use the DeviceManager on
[readthedocs](https://devicemanager.readthedocs.io/en/latest/). There you will also find some
examples, the API documentation on more...

Some useful example notebooks are located at [docs/source/examples](docs/source/examples).
