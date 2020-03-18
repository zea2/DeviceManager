#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The device manager module can be used to scan for connected devices and stores them persistently.

The devices are represented as `Device`-objects (especially `USBDevice` and `LANDevice`). To search
for connected devices of these types the `DeviceScanner`-classes are used. The `DeviceScanner` is a
general device scanner, that scans for all supported types. Additionally, there are the
`LANDeviceScanner` and the `USBDeviceScanner` which are used to only scan the specific protocols.
These are also contained by the general device scanner.
The master class of this module is the `DeviceManager` which allows its users to scan for devices
and also to store them persistently in a file. The device manager contains a general device scanner
and a dictionary to store devices by a user-defined name. The whole class is serializable as a JSON
formatted file from which it can be loaded, too.
"""

# Import relevant classes from this module
from .device import *  # base device, specific devices and device type enum
from .manager import *  # device manager that can persistently store devices
from .scanner import *  # base device scanner and specific device scanners

__version__ = "0.2.1"
