#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Device scanners working on windows systems.

Authors:
    Lukas Lankes, Forschungszentrum Jülich GmbH - ZEA-2, l.lankes@fz-juelich.de
"""

import sys
if sys.platform != "win32":
    raise ImportError("Windows-specific device scanners are only importable on windows systems.")

import re
import subprocess
import typing

import win32com.client

from ._base import BaseDeviceScanner, BaseLANDeviceScanner
from ..device import USBDevice, LANDevice

__all__ = ["Win32USBDeviceScanner", "Win32LANDeviceScanner"]

####################################################################################################


class Win32USBDeviceScanner(BaseDeviceScanner):
    """A device scanner that scans for usb devices on linux systems. It scans all usb ports for
    devices.
    """

    def __init__(self, **kwargs):
        super().__init__()
        self._wmi = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        self._wbem = self._wmi.ConnectServer(".", "root\\cimv2")

    @staticmethod
    def _device_from_raw(raw_device) -> USBDevice:
        """Converts a raw device provided from the windows device manager into a `USBDevice`-object.

        Args:
            raw_device: A device provided from the windows device manager as result of scanning all
                        known PNP devices.

        Returns:
            USBDevice: The `raw_device` converted into a `USBDevice`-object.
        """
        if raw_device.CreationClassName != "Win32_PnPEntity":
            raise TypeError("Expected \"Win32_PnPEntity\", got \"{}\" instead.".format(
                raw_device.CreationClassName))
        if raw_device.PNPClass != "USB":
            # Only usb devices are accepted
            raise TypeError("Expected PNP class \"USB\", got \"{}\" instead.".format(
                raw_device.PNPClass))

        dev = USBDevice()
        try:
            dev.address = raw_device.DeviceID
            # On win32 usb devices have many ids, that can be used to connect to the device
            dev.address_aliases = list(dict.fromkeys([*raw_device.HardwareID,
                                                      *raw_device.CompatibleID]))
        except AttributeError as exc:
            raise TypeError("Could not extract device id and hardware id from Win32_PnPEntity") \
                from exc

        device_type, attributes, instance_id = _analyse_win32_device_ids(dev.all_addresses)

        if device_type != "USB":
            # The pnp class (from the device id) also must be usb. Sometimes there are some PCI
            # devices found.
            raise TypeError("Expected PNP class \"USB\", got \"{}\" instead.".format(device_type))

        if instance_id is not None and "&" not in instance_id:
            # If ampersands are contained in the instance id, it cannot be a serial number
            dev.serial = instance_id

        # Readout the device attributes
        for key, value in attributes.items():
            if key == "VID":
                dev.vendor_id = int(value, base=16)
            elif key == "PID":
                dev.product_id = int(value, base=16)
            elif key == "REV":
                dev.revision_id = int(value, base=16)

        return dev

    def _scan(self, rescan: bool) -> typing.Sequence[USBDevice]:
        """Scans all PNP devices from the windows device manager and filters the USB devices.

        Args:
            rescan: True, to scan again. False, if you only want to scan, if there are no
                    results from a previous scan.
        """
        if len(self._devices) > 0 and not rescan:
            # Only scan if rescan is True or no devices were found, yet
            return self._devices

        self._devices.clear()
        # Get all plug-and-play devices from the windows device manager
        raw_devices = self._wbem.ExecQuery("SELECT * FROM Win32_PnPEntity")
        for raw_dev in raw_devices:
            try:
                dev = self._device_from_raw(raw_dev)
                self._devices.append(dev)
            except (TypeError, AttributeError, ValueError):
                pass
        return tuple(self._devices)


class Win32LANDeviceScanner(BaseLANDeviceScanner):
    """A device scanner that scans the local network for ethernet devices.

    Args:
        **kwargs:
          - nmap_search_path: One or multiple paths where to search for the nmap executable.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Regular Expression: "  <ip address>  <hardware type>  <mac address>  ..."
        self._arp_regex = re.compile(r"^[ \t]*((?:\d{1,3}\.){3}\d{1,3})[ \t]+"
                                     r"([0-9A-Fa-f]{2}[.:\-]){5}([0-9A-Fa-f]{2})")

    def _get_arp_cache(self) -> typing.Dict[str, LANDevice]:
        """Runs the arp command and extracts ip and mac addresses from the command's output.

        Returns:
            dict: A dictionary, mapping strings to `LANDevice`s. The dictionary contains all results
                  of the arp command, that contain a valid ip and mac address.
        """
        devices = {}

        try:
            # Run "arp -a", to retrieve all mac addresses from the ARP-cache
            process = subprocess.Popen(["arp", "-a"],
                                       bufsize=100000,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Command 'arp' was not found. Please, make sure it is "
                                    "installed.") from exc

        if process.returncode != 0:
            # The arp-command failed
            return devices

        raw_arp_out, raw_arp_err = process.communicate()
        arp_out = bytes.decode(raw_arp_out, errors="ignore")
        arp_err = bytes.decode(raw_arp_err, errors="ignore")

        if len(arp_err) > 0:
            # The arp-command failed
            return devices

        for line in arp_out.splitlines():
            if self._arp_regex.match(line):
                # Valid line due to regular expression
                components = line.split()
                ip_address = components[0]
                # The mac address can be found in third or second component, depending on whether
                # the <hardware type> is contained or not.
                try:
                    mac_address = LANDevice.format_mac(components[1])
                except (IndexError, TypeError):
                    # If no mac address was found, continue with next line
                    continue
                if mac_address in devices:
                    # If mac address is already known, IP address is added to the address aliases
                    if ip_address not in devices[mac_address].all_addresses:
                        devices[mac_address].address_aliases = [
                            *devices[mac_address].address_aliases,
                            ip_address]
                else:
                    # Unknown mac address: Create a new ethernet device
                    dev = LANDevice()
                    dev.address = ip_address
                    dev.mac_address = mac_address
                    devices[mac_address] = dev
        return devices


def _analyse_win32_device_ids(ids: typing.Iterable[str]) \
        -> typing.Tuple[str, typing.Dict[str, str], typing.Optional[str]]:
    """Analyses the windows devices ids of usb devices and extracts the pnp class, the device's
    identifiers and the instance id.

    Args:
        ids: A list of device ids of the same device.

    Returns:
        tuple of str: device's pnp class (e.g. USB, PCI)
                 dict: Device attributes (e.g. VID: vendor id, PID: product id, REV: revision code)
                 str (optional): instance id (often the serial number)
    """
    device_class = None
    items = {}
    instance_id = None

    for device_id in ids:
        components = device_id.split("\\")
        if len(components) < 2:
            continue  # At least to components expected
        if device_class is None:
            # Save device's pnp class of first valid device id
            device_class = components[0]
        elif device_class != components[0]:
            # Compare device's pnp class with first device, to ensure they are the same
            raise ValueError("Different values for device class: {}, {}".format(device_class,
                                                                                components[0]))
        # If length is at least 3, the last component contains the instance id
        if len(components) > 2:
            # Use the last components as instance id
            tmp_instance_id = "\\".join(components[2:])
            if instance_id is None:
                # Save the first valid instance id
                instance_id = tmp_instance_id
            elif instance_id != tmp_instance_id:
                # Compare the next valid instance ids to the first one, to ensure they are all the
                # same. If a different one is found, take the longest one, as soon as they are at
                # least partly equal.
                if instance_id.startswith(tmp_instance_id):
                    pass
                elif tmp_instance_id.startswith(instance_id):
                    instance_id = tmp_instance_id
                else:
                    # Raise an error, if another instance id was found, that is not at least partly
                    # equal to the other(s).
                    raise ValueError("Different values for instance id: {}, {}".format(
                        instance_id, tmp_instance_id))

        # The device's attributes are separated with an ampersand
        key_values = components[1].split("&")

        for key_value in key_values:
            try:
                # Split key and value of an attribute. These are separated with an underscore
                key, value = key_value.split('_')
            except ValueError:
                # If the attributes are not matching the expected format, continue with the next one
                continue
            key = key.upper()  # Only use uppercase keys
            if key not in items:
                # Add new key-value-pair
                items[key] = value
            elif items[key] != value:
                # Different values for the same key are not allowed
                raise ValueError("Different values for \"{}\": {}, {}".format(key, items[key],
                                                                              value))
    return device_class, items, instance_id
