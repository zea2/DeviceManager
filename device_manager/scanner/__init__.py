#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The device scanners are usefull to scan for connected devices of different types.

There are special device scanners (like `USBDeviceScanner` and `LANDeviceScanner`). These are used
to scan a specific protocol for connected devices. They are implemented for windows and linux to
make them work on the most common platforms. The windows and linux specific classes are imported
automatically depending on your system. Additionally, there is the general `DeviceScanner` that uses
the specific device scanners inside. So this class can be used to scan for different device types if
the type is unknown or if the user specifies a specific type, the scan is focused on this type.

Examples:
    s = DeviceScanner()  # Creates the general device scanner
    ls = s.list_devices()  # Lists all connected devices that can be found directly
    d1 = s.find_device(serial="1234567890AB")  # Returns a (usb) device with the requested serial no
    d2 = s.find_device(mac_address="12:34:56:78:90:AB")  # A (lan) device matching the mac address
    l = s["lan"].list_devices()  # Lists all knwon lan devices (maybe not all)
    l = s["lan"].nmap.scan(...)  # Scans for ethernet devices which should find all devices matching
                                 # the request. For more information see `NMAPWrapper`

Authors:
    Lukas Lankes, Forschungszentrum Jülich GmbH - ZEA-2, l.lankes@fz-juelich.de
"""

import sys
import typing

from ._base import BaseDeviceScanner
from ..device import DeviceType, Device, DeviceTypeDict, DeviceTypeType

# Import specific device scanners depending on current platform
if sys.platform == "win32":
    # Device scanners when working on windows
    from ._win32 import Win32USBDeviceScanner as USBDeviceScanner
    from ._win32 import Win32LANDeviceScanner as LANDeviceScanner
else:
    # Device scanners when working on other platforms (especially linux) that are usually unix based
    from ._linux import LinuxUSBDeviceScanner as USBDeviceScanner
    from ._linux import LinuxLANDeviceScanner as LANDeviceScanner

__all__ = ["DeviceScanner", "USBDeviceScanner", "LANDeviceScanner"]

####################################################################################################


class DeviceScanner(BaseDeviceScanner):
    """A general device scanner that contains all supported specific device scanners.

    Calling the `BaseDeviceScanner`-functions on this object causes the scanner to search in all
    protocols. If only a specific device type required, use the `__getitem__`-operator to specify
    the device type.
    """

    def __init__(self, **kwargs):
        super().__init__()
        self._scanners = DeviceTypeDict()
        self._scanners[DeviceType.USB] = USBDeviceScanner(**kwargs)
        self._scanners[DeviceType.LAN] = LANDeviceScanner(**kwargs)

    def _scan(self, rescan: bool) -> typing.Sequence[Device]:
        """Scans all connected devices of all supported types (usb and ethernet).

        Args:
            rescan: True, if the ports should be scanned again. False, if you only want to scan,
                    if there are no results from a previous scan.
        """
        self._devices.clear()
        # Scanning for all supported device types.
        for scanner in self._scanners.values():
            devices = scanner._scan(rescan)
            self._devices.extend(devices)
        return tuple(self._devices)

    def __getitem__(self, device_type: typing.Optional[DeviceTypeType]) -> BaseDeviceScanner:
        """Returns the corresponding device scanner for the requested `DeviceType`.

        Args:
            device_type: A `DeviceType`, a string that identifies a scanner type or None. A scanner
                         that scans for this device type is returned.

        Returns:
            BaseDeviceScanner: A device scanner, that scans for the passed device type. Or self, if
                               `device_type` is None.
        """
        if device_type is None:
            # For simplification, if None is passed, `self` is returned.
            return self
        else:
            # The `DeviceTypeDict` will automatically resolve the key, if it is a string.
            return self._scanners[device_type]

    def __iter__(self):
        """Returns iter(self)"""
        return self._scanners.__iter__()

    def __contains__(self, key: typing.Optional[DeviceTypeType]) -> bool:
        """Returns True, if self contains key. Otherwise, False."""
        if key is None:
            return True
        return self._scanners.__contains__(key)
