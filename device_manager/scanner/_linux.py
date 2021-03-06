#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Device scanners working on linux systems."""

import os
import sys
if sys.platform != "linux":
    if "DEVMAN_NO_IMPORT_ERROR" not in os.environ or \
            str(os.environ["DEVMAN_NO_IMPORT_ERROR"]) not in ["True", "1"]:
        raise ImportError("Linux-specific device scanners are only importable on linux systems")

import re
import subprocess
import typing

import pyudev

from ._base import BaseDeviceScanner, BaseLANDeviceScanner
from ..device import USBDevice, LANDevice

__all__ = ["LinuxUSBDeviceScanner", "LinuxLANDeviceScanner"]

####################################################################################################


class LinuxUSBDeviceScanner(BaseDeviceScanner):
    """A device scanner that scans for usb devices on linux systems. It scans all usb ports for
    devices.
    """

    def __init__(self):
        super().__init__()
        self._context = pyudev.Context()

    @staticmethod
    def _device_from_raw(raw_device: pyudev.Device) -> USBDevice:
        """Converts a raw device provided from pyudev into a `USBDevice`-object.

        Args:
            raw_device: A device provided from pyudev as result of scanning all usb ports.

        Returns:
            USBDevice: The `raw_device` converted into a `USBDevice`-object.
        """
        if not isinstance(raw_device, pyudev.Device):
            raise TypeError("Expected \"pyudev.Device\", got \"{}\" instead.".format(
                type(raw_device)))
        try:
            device_type = raw_device.properties["SUBSYSTEM"].upper()
        except (KeyError, AttributeError):
            raise TypeError("Could not specify the device's subsystem, expected: \"USB\".")
        if device_type != "USB":
            raise TypeError("Expected subsystem \"USB\", got \"{}\" instead.".format(device_type))

        dev = USBDevice()

        try:
            dev.address = raw_device.device_path
        except (AttributeError, TypeError) as exc:
            # When the raw device does not contain a path, it makes no sense
            raise TypeError("Could not get device path from pyudev.Device") from exc

        # Extracting device properties
        if "DEVNAME" in raw_device.properties:
            dev.address_aliases = [raw_device.properties["DEVNAME"]]
        if "ID_VENDOR_ID" in raw_device.properties:
            dev.vendor_id = int(raw_device.properties["ID_VENDOR_ID"], base=16)
        if "ID_MODEL_ID" in raw_device.properties:
            dev.product_id = int(raw_device.properties["ID_MODEL_ID"], base=16)
        if "ID_REVISION" in raw_device.properties:
            dev.revision_id = int(raw_device.properties["ID_REVISION"], base=16)
        if "ID_SERIAL_SHORT" in raw_device.properties:
            dev.serial = raw_device.properties["ID_SERIAL_SHORT"]

        return dev

    def _scan(self, rescan: bool) -> typing.Sequence[USBDevice]:
        """Scans all usb ports for devices.

        Args:
            rescan: True, if the ports should be scanned again. False, if you only want to scan,
                    if there are no results from a previous scan.
        """
        if len(self._devices) > 0 and not rescan:
            return self._devices

        self._devices.clear()
        raw_devices = self._context.list_devices()
        for raw_dev in raw_devices:
            try:
                dev = self._device_from_raw(raw_dev)
                self._devices.append(dev)
            except (TypeError, ValueError):
                pass
        return tuple(self._devices)


class LinuxLANDeviceScanner(BaseLANDeviceScanner):
    """A device scanner that scans the local network for ethernet devices.

    Args:
        **kwargs:
          - nmap_search_path: One or multiple paths where to search for the nmap executable.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Regular Expression: "  <ip address>  <hardware type>  <mac address>  ..."
        self._arp_regex = re.compile(r"^[ \t]*((?:\d{1,3}\.){3}\d{1,3})[ \t]+(\w*[ \t]+)?"
                                     r"([0-9A-Fa-f]{2}[.:\-]){5}([0-9A-Fa-f]{2})")

    def _get_arp_cache(self) -> typing.Dict[str, LANDevice]:
        """Runs the arp command and extracts ip and mac addresses from the command's output.

        Returns:
            dict: A dictionary, mapping strings to `LANDevice`s. The dictionary contains all results
                  of the arp command, that contain a valid ip and mac address.
        """
        devices = {}

        try:
            # Run "arp -n", to retrieve all mac addresses from the ARP-cache
            process = subprocess.Popen(["arp", "-n"],
                                       bufsize=100000,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
        except FileNotFoundError as exc:
            raise FileNotFoundError("Command 'arp' was not found. Please, make sure \"net-tools\" "
                                    "is installed.") from exc

        raw_arp_out, raw_arp_err = process.communicate()

        if process.returncode != 0:
            # The arp-command failed
            return devices

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
                for i in [2, 1]:
                    try:
                        mac_address = LANDevice.format_mac(components[i])
                        break
                    except (IndexError, TypeError):
                        pass
                else:
                    # If no mac address was found, continue with next line
                    continue
                if mac_address in devices:
                    # If mac address is already known, ip address is added to the address aliases
                    if ip_address not in devices[mac_address].all_addresses:
                        devices[mac_address].address_aliases = [
                            *devices[mac_address].address_aliases,
                            ip_address]
                else:
                    dev = LANDevice()
                    dev.address = ip_address
                    dev.mac_address = mac_address
                    devices[mac_address] = dev

        return devices
