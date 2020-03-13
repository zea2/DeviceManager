#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The device scanners are useful to scan for connected devices of different types.

There are special device scanners (like `USBDeviceScanner` and `LANDeviceScanner`). These are used
to scan a specific protocol for connected devices. They are implemented for windows and linux to
make them work on the most common platforms. The windows and linux specific classes are imported
automatically depending on your system. Additionally, there is the general `DeviceScanner` that uses
the specific device scanners inside. So this class can be used to scan for different device types if
the type is unknown or if the user specifies a specific type, the scan is focused on this type.

Examples:
    Creating a general device scanner:

    >>> s = DeviceScanner()

    Listing all connected devices that can be found directly:

    >>> devices = s.list_devices()

    Finding devices by their identifiers

    >>> usb_device = s.find_devices(serial="1234567890AB")
    >>> lan_device = s.find_devices(mac_address="12:34:56:78:90:AB")

    To only search for a specific device type, you can access the specific `DeviceScanner`s by using
    the `__getitem__` operator. This speeds up the search for the device.

    >>> usb_device = s["usb"].find_devices(serial="1234567890AB")
    >>> lan_devices = s["lan"].list_devices()

    For better results when searching for ethernet devices, nmap can be used to scan the network.
    For more information take a look at the `NMAPWrapper`.

    >>> s["lan"].nmap.scan(...)
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
elif sys.platform == "linux":
    # Device scanners when working on other platforms (especially linux) that are usually unix based
    from ._linux import LinuxUSBDeviceScanner as USBDeviceScanner
    from ._linux import LinuxLANDeviceScanner as LANDeviceScanner
else:
    raise OSError("The platform \"{}\" is not supported".format(sys.platform))

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
            devices = scanner._scan(rescan)  # pylint: disable=protected-access
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
