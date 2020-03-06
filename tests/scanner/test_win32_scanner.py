#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script for testing the module device_manager.scanner._win32.

This script tests the following entities:
- class Win32USBDeviceScanner
- class Win32LANDeviceScanner

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


@unittest.skipUnless(sys.platform == "win32", "Requires Windows")
class TestWin32ScannerImport(unittest.TestCase):
    def test_import(self):
        from device_manager.scanner._win32 import Win32USBDeviceScanner, Win32LANDeviceScanner

        self.assertIs(USBDeviceScanner, Win32USBDeviceScanner)
        self.assertIs(LANDeviceScanner, Win32LANDeviceScanner)

    def test_import_error(self):
        with self.assertRaises(ImportError, msg="Importing linux-specific device scanners should "
                                                "fail on windows"):
            import device_manager.scanner._linux


@unittest.skipUnless(sys.platform == "win32", "Requires Windows")
class TestWin32USBDeviceScanner(unittest.TestCase):
    class MockWin32Entity:
        def __init__(self, class_name, pnp_class, vendor_id, product_id, revision_id, instance_id):
            device_id = "{pnp}\\VID_{vid:04X}&PID_{pid:04X}\\{inst}".format(
                pnp=pnp_class, vid=vendor_id, pid=product_id, inst=instance_id)
            hardware_ids = ["{pnp}\\VID_{vid:04X}&PID_{pid:04X}".format(
                pnp=pnp_class, vid=vendor_id, pid=product_id)]
            if revision_id is not None:
                hardware_ids.append("{pnp}\\VID_{vid:04X}&PID_{pid:04X}&REV_{rev:04X}".format(
                    pnp=pnp_class, vid=vendor_id, pid=product_id, rev=revision_id))

            compatible_ids = ["{pnp}\\{pnp}00_HUB".format(pnp=pnp_class)]

            self.CreationClassName = class_name
            self.PNPClass = pnp_class
            self.DeviceID = device_id
            self.HardwareID = hardware_ids
            self.CompatibleID = compatible_ids

            self.device = USBDevice()
            self.device.address = device_id
            self.device.address_aliases = [*hardware_ids, *compatible_ids]
            self.device.vendor_id = vendor_id
            self.device.product_id = product_id
            self.device.revision_id = revision_id
            if "&" not in instance_id:
                self.device.serial = instance_id

    class MockWMIConnectServer:
        def ExecQuery(self, *args, **kwargs):
            raise NotImplementedError()

    def setUp(self) -> None:
        self.scanner = USBDeviceScanner()

        self.valid_devices = [
            self.MockWin32Entity("Win32_PnPEntity", "USB", 0x12AB, 0x0123, 0x0100, "01234ABCDEF"),
            self.MockWin32Entity("Win32_PnPEntity", "USB", 0x5A67, 0xAB98, None, "012345678AB"),
            self.MockWin32Entity("Win32_PnPEntity", "USB", 0x1234, 0x9871, 0x0010, "123&125&123"),
            self.MockWin32Entity("Win32_PnPEntity", "USB", 0, 0, 0, "")
        ]
        self.invalid_devices = [
            self.MockWin32Entity("Win32_PnPEntity", "PCI", 0x12AB, 0x0123, 0x0100, "INVALID1"),
            self.MockWin32Entity("Win32_PnPEntity", "usb", 0x1234, 0xFEDC, 0x0000, "INVALID2"),
            self.MockWin32Entity("invalid", "USB", 0x12AB, 0x0123, 0x0100, "INVALID3")
        ]

        tmp_dev = self.MockWin32Entity("Win32_PnPEntity", "USB", 0, 0, 0, "INVALID4")
        del tmp_dev.DeviceID  # Missing device id
        self.invalid_devices.append(tmp_dev)
        tmp_dev = self.MockWin32Entity("Win32_PnPEntity", "USB", 0, 0, 0, "INVALID5")
        tmp_dev.DeviceID = "USB"  # Device id too short
        self.invalid_devices.append(tmp_dev)
        tmp_dev = self.MockWin32Entity("Win32_PnPEntity", "USB", 0, 0, 0, "INVALID5")
        tmp_dev.DeviceID = "USB\\VID_0000&PID_0000_0000"  # Invalid device id format
        self.invalid_devices.append(tmp_dev)
        tmp_dev = self.MockWin32Entity("Win32_PnPEntity", "USB", 0, 0, 0, "INVALID6")
        tmp_dev.CompatibleID = ["USBXYZ\\abcdef1234"]  # Invalid PNP class in device id
        self.invalid_devices.append(tmp_dev)
        tmp_dev = self.MockWin32Entity("Win32_PnPEntity", "USB", 0, 0, 0, "INVALID6")
        tmp_dev.CompatibleID = ["USB\\0123456\\INVALIDXXXX"]  # Not matching id
        self.invalid_devices.append(tmp_dev)
        tmp_dev = self.MockWin32Entity("Win32_PnPEntity", "PCI", 0, 0, 0, "INVALID7")
        tmp_dev.PNPClass = "USB"
        self.invalid_devices.append(tmp_dev)
        tmp_dev = self.MockWin32Entity("Win32_PnPEntity", "USB", 0, 0, 0, "INVALID8")
        tmp_dev.HardwareID.append(self.valid_devices[0].DeviceID)  # Not matching device id
        self.invalid_devices.append(tmp_dev)
        tmp_dev = self.MockWin32Entity("Win32_PnPEntity", "USB", 0, 0, 0, "INVALID9")
        tmp_dev.HardwareID.append(self.valid_devices[0].HardwareID[0])  # Not matching hardware id
        self.invalid_devices.append(tmp_dev)

        self.invalid_devices.append(tmp_dev)

        self.all_devices = [*self.valid_devices, *self.invalid_devices]

        self.wmi_mock = unittest.mock.MagicMock(return_value=self.all_devices)
        self.wmi_mock_expected_argument = "SELECT * FROM Win32_PnPEntity"
        self.scanner._wbem = self.MockWMIConnectServer()  # COMObjects cannot be mocked
        self.scanner._wbem.ExecQuery = self.wmi_mock

    def test_scan(self):
        self.wmi_mock.reset_mock()

        devices = self.scanner.list_devices(rescan=True)
        self.wmi_mock.assert_called_once_with(self.wmi_mock_expected_argument)

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

        self.wmi_mock.reset_mock()
        rescan_devices = self.scanner.list_devices()
        self.wmi_mock.assert_not_called()
        self.assertSequenceEqual(devices, rescan_devices,
                                 msg="The second scan with Win32USBDeviceScanner should return the "
                                     "same values without forcing a rescan")

        self.wmi_mock.reset_mock()
        old_return_value = self.wmi_mock.return_value
        try:
            self.wmi_mock.return_value = [self.valid_devices[0]]
            rescan_devices = self.scanner.list_devices(rescan=True)
        finally:
            # Reset return value
            self.wmi_mock.return_value = old_return_value
        self.wmi_mock.assert_called_once_with(self.wmi_mock_expected_argument)
        self.assertSequenceEqual((self.valid_devices[0].device,), rescan_devices,
                                 msg="A forced rescan with Win32USBDeviceScanner should return "
                                     "other values than before")


@unittest.skipUnless(sys.platform == "win32", "Requires Windows")
class TestWin32LANDeviceScanner(unittest.TestCase):
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
            b"Interface: 192.168.1.98 --- 0x10",
            b"  Internet Address      Physical Address      Type",
            b"  192.168.1.1           01-f0-60-b4-da-10     dynamic",
            b"  192.168.1.3\td3-1e-52-7f-2d-81 dynamic",  # Tabs are also accepted
            b"  192.168.1.7           03-83-65-cf-c4-cd",  # Last column(s) are ignored
            b"  192.168.1.14          f0:1a:bd:f0:2f:a2     dynamic",  # Colons are allowed in MAC
            b"  192.168.1.15          50.9a.71.5d.24.e2     dynamic",  # Dots are allowed in MAC
            b"  192.168.1.23          01-41-56-0C-EB-01     dynamic",
            b"  192.168.1.165         f5-6D:03-5e.45-1F     dynamic",
            b"  192.168.1.255         ff-ff-ff-ff-ff-ff     static",
            b"  224.0.0.22            01-00-5e-00-00-16     static",
            b"",
            b"Interface: 192.168.20.27 --- 0x17",
            b"  Internet Address      Physical Address      Type",
            b"192.168.20.143        01-f0-61-b4-d9-10     dynamic",  # Leading spaces not required
            b"  192.168.20.251        d3-1a-52-7f-2f-82     dynamic",
            b"  192.168.20.255        ff-ff-ff-ff-ff-ff     static",  # Broadcast (duplicate)
            b"  224.0.0.22            01-00-5e-00-00-16     static",  # Multicast (duplicate)
            b"",

            # Invalid lines ...
            b"Interface: 192.168.24.75 --- 0x19",
            b"  192.168.24.10                               dynamic",  # Invalid: no MAC
            b"  192.168.24.11",  # Invalid: no MAC
            b"  192.168.24            01-f0-61-b4-d9-10     dynamic",  # Invalid IP
            b"  192.168.24.251        d3-1G-53-7f-2f-82     dynamic",  # Invalid MAC
            b"  192.168.24.252  abc   00-1a-53-7f-2f-82     dynamic",  # Invalid line format
            b""
        ])
        self.expected_result = [
            self.make_lan_device("192.168.1.1", "01-f0-60-b4-da-10"),
            self.make_lan_device("192.168.1.3", "d3-1e-52-7f-2d-81"),
            self.make_lan_device("192.168.1.7", "03-83-65-cf-c4-cd"),
            self.make_lan_device("192.168.1.14", "f0:1a:bd:f0:2f:a2"),
            self.make_lan_device("192.168.1.15", "50.9a.71.5d.24.e2"),
            self.make_lan_device("192.168.1.23", "01-41-56-0C-EB-01"),
            self.make_lan_device("192.168.1.165", "f5-6D:03-5e.45-1F"),
            self.make_lan_device("192.168.1.255", "ff-ff-ff-ff-ff-ff",
                                 aliases=["192.168.20.255"]),  # Same mac-address -> same LANDevice
            self.make_lan_device("224.0.0.22", "01-00-5e-00-00-16"),
            self.make_lan_device("192.168.20.143", "01-f0-61-b4-d9-10"),
            self.make_lan_device("192.168.20.251", "d3-1a-52-7f-2f-82")
        ]

        self.popen_mock = self.MockPopen()
        self.popen_communicate_mock = unittest.mock.MagicMock(return_value=(self.arp_output, b""))
        self.popen_mock.communicate = self.popen_communicate_mock
        self.popen_returncode_mock = unittest.mock.PropertyMock(return_value=0)
        type(self.popen_mock).returncode = self.popen_returncode_mock
        self.popen_init_mock = unittest.mock.MagicMock(return_value=self.popen_mock)

        setattr(subprocess, "Popen", self.popen_init_mock)
        self.popen_init_args = (["arp", "-a"],)
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
