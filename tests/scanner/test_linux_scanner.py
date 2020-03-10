#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script for testing the module device_manager.scanner._linux.

This script tests the following entities:
- class LinuxUSBDeviceScanner
- class LinuxLANDeviceScanner

Authors:
    Lukas Lankes, Forschungszentrum Jülich GmbH - ZEA-2, l.lankes@fz-juelich.de
"""

import os
import subprocess
import sys
import unittest
import unittest.mock

from device_manager.device import USBDevice, LANDevice
from device_manager.scanner import USBDeviceScanner, LANDeviceScanner


@unittest.skipIf(sys.platform == "win32", "Requires Linux")
class TestLinuxScannerImport(unittest.TestCase):
    def test_import(self):
        from device_manager.scanner._linux import LinuxUSBDeviceScanner, LinuxLANDeviceScanner

        self.assertIs(USBDeviceScanner, LinuxUSBDeviceScanner)
        self.assertIs(LANDeviceScanner, LinuxLANDeviceScanner)

    def test_import_error(self):
        with self.assertRaises(ImportError, msg="Importing windows-specific device scanners should "
                                                "fail on linux"):
            import device_manager.scanner._win32


@unittest.skipIf(sys.platform == "win32", "Requires Linux")
class TestLinuxUSBDeviceScanner(unittest.TestCase):
    class MockPyudevDevice(unittest.mock.Mock):
        def __init__(self, path, subsystem, name,  vendor_id, product_id, revision_id, serial, cls):
            super().__init__(spec=cls)
            self.path = path
            if path is not None:
                self.device_path = path
            self.name = name
            self.subsystem = subsystem
            self.vendor_id = vendor_id
            self.product_id = product_id
            self.revision_id = revision_id
            self.serial = serial

        @property
        def properties(self):
            properties = {}
            if self.name is not None:
                properties["DEVNAME"] = self.name
            if self.subsystem is not None:
                properties["SUBSYSTEM"] = self.subsystem
            if self.vendor_id is not None:
                properties["ID_VENDOR_ID"] = hex(self.vendor_id)
            if self.product_id is not None:
                properties["ID_MODEL_ID"] = hex(self.product_id)
            if self.revision_id is not None:
                properties["ID_REVISION"] = hex(self.revision_id)
            if self.serial is not None:
                properties["ID_SERIAL_SHORT"] = self.serial
            return properties

        @property
        def device(self):
            device = USBDevice()
            device.address = self.path
            device.address_aliases = [self.name]
            device.vendor_id = self.vendor_id
            device.product_id = self.product_id
            device.revision_id = self.revision_id
            device.serial = self.serial
            return device

    def setUp(self) -> None:
        import pyudev

        self.scanner = USBDeviceScanner()

        self.valid_devices = [
            self.MockPyudevDevice("/sys/devices/pci0000:00/0000:00:06.0/usb2", "usb",
                                  "/dev/bus/usb/002/001", 0x1234, 0x5678, 0x0104, "1234ABCD09",
                                  pyudev.Device),
            self.MockPyudevDevice("/sys/devices/pci0000:00/0000:00:06.0/usb0", "usb",
                                  None, 0xAB02, 0xDEF1, 0x0A00, "1234ABCD09", pyudev.Device),
            self.MockPyudevDevice("/sys/devices/pci0000:00/0000:00:06.0/usb4", "usb",
                                  "/dev/bus/usb/002/002", 0x0905, 0xB00F, 0x105A, None,
                                  pyudev.Device),
            self.MockPyudevDevice("/sys/devices/pci0000:00/0000:00:06.0/usb1", "usb",
                                  "/dev/bus/usb/001/001", 0x88B9, 0x3D04, None, "ABCDEF987601",
                                  pyudev.Device),
            self.MockPyudevDevice("/sys/devices/pci0000:00/0000:00:06.0/usb3", "usb",
                                  None, None, None, None, None, pyudev.Device)
        ]
        self.invalid_devices = [
            self.MockPyudevDevice("/sys/devices/pci0000:00/0000:00:06.0/usb5", "pci",
                                  "/dev/bus/usb/002/005", 0x1234, 0x5678, 0x0104, "INVALID1",
                                  pyudev.Device),
            self.MockPyudevDevice(None, "usb",
                                  "/dev/bus/usb/009/003", 0x1234, 0x5678, 0x0104, "INVALID2",
                                  pyudev.Device),
            self.MockPyudevDevice("/sys/devices/pci0000:00/0000:00:06.0/usb6", None,
                                  "/dev/bus/usb/002/008", 0x1234, 0x5678, 0x0104, "INVALID3",
                                  pyudev.Device),
            self.MockPyudevDevice("/sys/devices/pci0000:00/usb7", "usb",
                                  "/dev/bus/usb/004", 0x1234, 0x5678, 0x0104, "INVALID4", str)
        ]

        self.all_devices = [*self.valid_devices, *self.invalid_devices]

        self.context_mock = unittest.mock.MagicMock(return_value=self.all_devices)
        self.scanner._context.list_devices = self.context_mock

    def test_scan(self):
        self.context_mock.reset()

        devices = self.scanner.list_devices(rescan=True)
        self.context_mock.assert_called_once_with()

        for dev in self.valid_devices:
            self.assertIn(dev.device, devices)
        for dev in self.invalid_devices:
            self.assertNotIn(dev.device, devices)

        for search_device in self.valid_devices:
            found_devices = self.scanner.find_devices(**search_device.device.unique_identifier)
            self.assertSequenceEqual((search_device.device,), found_devices,
                                     msg="The device which was searched by its unique identifiers "
                                         "was not found")
            found_devices = self.scanner.find_devices(address=search_device.device.address)
            self.assertSequenceEqual((search_device.device,), found_devices,
                                     msg="The device which was searched by address was not found")

        found_devices = self.scanner.find_devices(invalid_param="test")
        self.assertSequenceEqual(tuple(), found_devices,
                                 msg="Searching for an invalid parameter should not return any "
                                     "results")

    def test_scan_errors(self):
        devices = self.scanner.list_devices()

        self.context_mock.reset_mock()
        rescan_devices = self.scanner.list_devices()
        self.context_mock.assert_not_called()
        self.assertSequenceEqual(devices, rescan_devices,
                                 msg="The second scan with Win32USBDeviceScanner should return the "
                                     "same values without forcing a rescan")

        self.context_mock.reset_mock()
        old_return_value = self.context_mock.return_value
        try:
            self.context_mock.return_value = [self.valid_devices[0]]
            rescan_devices = self.scanner.list_devices(rescan=True)
        finally:
            # Reset return value
            self.context_mock.return_value = old_return_value
        self.context_mock.assert_called_once_with()
        self.assertSequenceEqual((self.valid_devices[0].device,), rescan_devices,
                                 msg="A forced rescan with Win32USBDeviceScanner should return "
                                     "other values than before")


@unittest.skipIf(sys.platform == "win32", "Requires Linux")
class TestLinuxLANDeviceScanner(unittest.TestCase):
    class MockPopen:
        def communicate(self, input=None):
            raise NotImplementedError()

        @property
        def returncode(self):
            raise NotImplementedError()

    @staticmethod
    def make_lan_device(address, mac_address, aliases=None):
        device = LANDevice()
        device.address = address
        device.address_aliases = aliases
        device.mac_address = mac_address
        return device

    def setUp(self) -> None:
        self.scanner = LANDeviceScanner()

        self.arp_output = os.linesep.encode().join([
            b"Address                  HWtype  HWaddress           Flags Mask            Iface",
            b"192.168.10.14            ether   02:a7:71:36:9d:f2   C                     enp0s3",
            b"192.168.10.18            ether   f3:85:9f:98:e8:21   C                     enp0s3",
            b"192.168.10.19                    12:62:8f:7c:de:2e   C                     enp0s3",
            b"192.168.10.36 de:ea:f1:17:8c:5c C enp0s3",
            b"192.168.10.39\tether   99:59:74:26:7a:d3   C                     enp0s3",
            b"192.168.10.81\tcd:eb:90:ae:13:67   C                     enp0s3",
            b"192.168.10.84            ether   32.c3.f6.62.49.a6   C                     enp0s3",
            b"192.168.10.165           ether   21-e4-b7-6e-84-b9   C                     enp0s3",
            b"192.168.10.174           ether   0E:3A:4D:B3:5E:1C   C                     enp0s3",
            b"192.168.10.175           ether   fD:95:57-02.2b-23   C                     enp0s3",
            b"192.168.10.177           ether   fd:95:57:02:2b:23",
            # Invalid lines ...
            b"192.168.10.203           ether                    ",  # Missing MAC
            b"192.168.10.204",  # Missing MAC
            b"192.168.10               ether   00:39:4e:23:96:fe",  # Invalid IP
            b"192.168.10.209           ether   35:3c:a5:92:46:4Y",  # Invalid MAC
            b"192.168.10.210  abcdefg  ether   35:3c:a5:92:46:4c",  # Invalid line format
            b""
        ])

        self.expected_result = [
            self.make_lan_device("192.168.10.14", "02:a7:71:36:9d:f2"),
            self.make_lan_device("192.168.10.18", "f3:85:9f:98:e8:21"),
            self.make_lan_device("192.168.10.19", "12:62:8f:7c:de:2e"),
            self.make_lan_device("192.168.10.36", "de:ea:f1:17:8c:5c"),
            self.make_lan_device("192.168.10.39", "99:59:74:26:7a:d3"),
            self.make_lan_device("192.168.10.81", "cd:eb:90:ae:13:67"),
            self.make_lan_device("192.168.10.84", "32.c3.f6.62.49.a6"),
            self.make_lan_device("192.168.10.165", "21-e4-b7-6e-84-b9"),
            self.make_lan_device("192.168.10.174", "0E:3A:4D:B3:5E:1C"),
            self.make_lan_device("192.168.10.175", "fD:95:57-02.2b-23",
                                 aliases=["192.168.10.177"])
        ]

        self.popen_mock = self.MockPopen()
        self.popen_communicate_mock = unittest.mock.MagicMock(return_value=(self.arp_output, b""))
        self.popen_mock.communicate = self.popen_communicate_mock
        self.popen_returncode_mock = unittest.mock.PropertyMock(return_value=0)
        type(self.popen_mock).returncode = self.popen_returncode_mock
        self.popen_init_mock = unittest.mock.MagicMock(return_value=self.popen_mock)

        setattr(subprocess, "Popen", self.popen_init_mock)
        self.popen_init_args = (["arp", "-n"],)
        self.popen_init_kwargs = {"bufsize": 100000,
                                  "stdin": subprocess.PIPE,
                                  "stdout": subprocess.PIPE,
                                  "stderr": subprocess.PIPE}

    def test_scan(self):
        self.popen_init_mock.reset_mock()
        self.popen_returncode_mock.reset_mock()
        self.popen_communicate_mock.reset_mock()

        # Test list devices
        devices = self.scanner.list_devices()
        self.popen_init_mock.assert_called_once_with(*self.popen_init_args,
                                                     **self.popen_init_kwargs)
        self.popen_returncode_mock.assert_called_once_with()
        self.popen_communicate_mock.assert_called_once_with()
        self.assertEqual(tuple(self.expected_result), devices,
                         msg="LANDeviceScanner.list_devices did not return the expected values")

        self.popen_init_mock.reset_mock()
        self.popen_returncode_mock.reset_mock()
        self.popen_communicate_mock.reset_mock()

        # Scanning after a scan that already got results should do nothing
        devices = self.scanner.list_devices()
        self.popen_init_mock.assert_not_called()
        self.popen_returncode_mock.assert_not_called()
        self.popen_communicate_mock.assert_not_called()

        # Test find device
        test_device = self.expected_result[0]
        devices = self.scanner.find_devices(mac_address=test_device.mac_address)
        self.assertSequenceEqual((test_device,), devices,
                                 msg="LANDeviceScanner.find_devices did not return the expected "
                                     "result")

    def test_scan_errors(self):
        self.popen_init_mock.reset_mock()
        self.popen_returncode_mock.reset_mock()
        self.popen_communicate_mock.reset_mock()

        # ARP command returns 1
        old_return_value = self.popen_returncode_mock.return_value
        self.popen_returncode_mock.return_value = 1
        devices = self.scanner.list_devices(rescan=True)
        self.popen_returncode_mock.return_value = old_return_value
        self.popen_init_mock.assert_called_once_with(*self.popen_init_args,
                                                     **self.popen_init_kwargs)
        self.popen_returncode_mock.assert_called_once_with()
        self.assertSequenceEqual(tuple(), devices,
                                 msg="When \"arp\" fails, the scanner should not find any devices")

        self.popen_init_mock.reset_mock()
        self.popen_returncode_mock.reset_mock()
        self.popen_communicate_mock.reset_mock()

        # ARP command prints to stderr
        old_return_value = self.popen_communicate_mock.return_value
        self.popen_communicate_mock.return_value = (self.arp_output, b"Some error occurred!")
        devices = self.scanner.list_devices(rescan=True)
        self.popen_communicate_mock.return_value = old_return_value
        self.popen_init_mock.assert_called_once_with(*self.popen_init_args,
                                                     **self.popen_init_kwargs)
        self.popen_returncode_mock.assert_called_once_with()
        self.assertSequenceEqual(tuple(), devices,
                                 msg="When \"arp\" prints to stderr, the scanner should not find "
                                     "any devices")

        # ARP command not found
        old_side_effect = self.popen_init_mock.side_effect
        self.popen_init_mock.side_effect = FileNotFoundError("Command \"arp\" not found")
        with self.assertRaises(FileNotFoundError,
                               msg="If the arp-command could not be found, searching for devices "
                                   "should raise an exception"):
            devices = self.scanner.list_devices(rescan=True)
        self.popen_init_mock.side_effect = old_side_effect
