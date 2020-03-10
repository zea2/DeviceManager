#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script for testing the module device_manager.device.

This script tests the following entities:
- class DeviceManager (including DeviceDict, DeviceTypeDict)
- function load_device_manager

Authors:
    Lukas Lankes, Forschungszentrum Jülich GmbH - ZEA-2, l.lankes@fz-juelich.de
"""

import contextlib
import os
import unittest
import unittest.mock

from device_manager.device import DeviceType, USBDevice, LANDevice
from device_manager.scanner import DeviceScanner
from device_manager.manager import DeviceManager, load_device_manager


class TestDeviceManager(unittest.TestCase):
    @staticmethod
    def make_usb_device(address, vendor, product, revision, serial, aliases=None) -> USBDevice:
        device = USBDevice()
        device.address = address
        device.address_aliases = aliases
        device.vendor_id = vendor
        device.product_id = product
        device.revision_id = revision
        device.serial = serial
        return device

    @staticmethod
    def make_lan_device(address, mac_address, aliases=None) -> LANDevice:
        device = LANDevice()
        device.address = address
        device.address_aliases = aliases
        device.mac_address = mac_address
        return device

    @contextlib.contextmanager
    def mock_device_scanner(self):
        init_device_scanner = DeviceScanner.__init__

        def mock_init_device_scanner(this, *args, **kwargs):
            init_device_scanner(this, *args, **kwargs)
            this._scanners[DeviceType.USB]._devices = self.usb_devices
            this._scanners[DeviceType.USB].mock_scan = unittest.mock.MagicMock(
                side_effect=lambda *a, **kw: tuple(self.usb_devices))
            this._scanners[DeviceType.USB]._scan = this._scanners[DeviceType.USB].mock_scan
            this._scanners[DeviceType.LAN]._devices = self.lan_devices
            this._scanners[DeviceType.LAN].mock_scan = unittest.mock.MagicMock(
                side_effect=lambda *a, **kw: tuple(self.lan_devices))
            this._scanners[DeviceType.LAN]._scan = this._scanners[DeviceType.LAN].mock_scan
            this._scanners[DeviceType.LAN].nmap._nmap = None

        with unittest.mock.patch.object(DeviceScanner, "__init__", mock_init_device_scanner):
            yield

    def setUp(self) -> None:
        self.usb_devices = [
            self.make_usb_device("USB\\0", 0x12AB, 0x0123, 0x0100, "01234ABCDEF"),
            self.make_usb_device("USB\\1", 0x5A67, 0xAB98, None, "012345678AB"),
            self.make_usb_device("USB\\2", 0x1234, 0x9871, 0x0010, None),
            self.make_usb_device("USB\\3", 0x2468, 0xFF30, 0x0123, "AGEHBD341B")
        ]
        self.lan_devices = [
            self.make_lan_device("192.168.10.81", "cd:eb:90:ae:13:67"),
            self.make_lan_device("192.168.10.84", "32.c3.f6.62.49.a6"),
            self.make_lan_device("192.168.10.165", "21-e4-b7-6e-84-b9"),
            self.make_lan_device("192.168.10.174", "0E:3A:4D:B3:5E:1C",
                                 aliases=["192.168.10.253", "192.168.10.254"]),
            self.make_lan_device("192.168.10.175", "fD:95:57-02.2b-23",
                                 aliases=["192.168.10.177"])
        ]

        with self.mock_device_scanner():
            self.manager = DeviceManager()

    def tearDown(self) -> None:
        print("### TD")

    def test_dictionary(self):
        self.manager["custom-dev-name"] = self.usb_devices[0]
        self.manager["custom-dev-name"] = self.lan_devices[0]
        self.assertIn("custom-dev-name", self.manager,
                      msg="New device-name was not added to device manager")
        self.assertEqual(self.usb_devices[0], self.manager["custom-dev-name", "usb"],
                         msg="USB device was not added to device manager")
        self.assertEqual(self.lan_devices[0], self.manager["custom-dev-name", "lan"],
                         msg="LAN device was not added to device manager")
        expected_dict = {DeviceType.USB: self.usb_devices[0],
                         DeviceType.LAN: self.lan_devices[0]}
        self.assertDictEqual(expected_dict, self.manager["custom-dev-name"],
                             msg="USB and LAN device were not stored in a dictionary correctly")
        self.assertIn(expected_dict, self.manager.values(),
                      msg="Did not found expected devices in DeviceManager.values")
        self.assertIn(("custom-dev-name", expected_dict), self.manager.items(),
                      msg="Did not found expected devices in DeviceManager.items")

        self.manager["my-usb-device"] = self.usb_devices[1]
        self.assertEqual(self.usb_devices[1], self.manager["my-usb-device"],
                         msg="Did not receive the expected result for key \"my-usb-device\"")
        self.manager["my-lan-device"] = self.lan_devices[1]
        self.assertEqual(self.lan_devices[1], self.manager["my-lan-device"],
                         msg="Did not receive the expected result for key \"my-lan-device\"")

        self.assertEqual(3, len(self.manager),
                         msg="Invalid length of DeviceManager")

        for key in self.manager:
            self.assertIn(key, ["custom-dev-name", "my-lan-device", "my-usb-device"],
                          msg="Invalid key in DeviceManager")

        with self.assertRaises(KeyError, msg="Using an invalid key should raise an exception"):
            dev = self.manager["invalid-key"]
        with self.assertRaises(KeyError, msg="Requesting an unknown key should raise an exception"):
            dev = self.manager["my-usb-device", "lan"]
        with self.assertRaises(TypeError,
                               msg="A DeviceManager's key must be string or tuple of two strings"):
            dev = self.manager["my-usb-device", "usb", "invalid"]

        with self.assertRaises(TypeError, msg="Invalid key type did not cause an error"):
            self.manager[123] = self.lan_devices[2]
        with self.assertRaises(ValueError, msg="Wrong device type added to DeviceManager"):
            self.manager["valid-key", "lan"] = USBDevice()
        self.assertNotIn("valid-key", self.manager, msg="Unexpected key was added to DeviceManager")
        with self.assertRaises(TypeError, msg="Invalid value type did not cause an error"):
            self.manager["valid-key"] = 123
        self.assertNotIn("valid-key", self.manager, msg="Unexpected key was added to DeviceManager")

        del self.manager["my-usb-device"]
        self.assertNotIn("my-usb-device", self.manager,
                         msg="Deleting an item of DeviceManager failed")
        del self.manager["custom-dev-name", "lan"]
        self.assertIn("custom-dev-name", self.manager,
                      msg="Deleted too much items from DeviceManager")
        self.assertIsInstance(self.manager["custom-dev-name"], USBDevice,
                              msg="Deleting a single item of DeviceTypeDict failed")
        del self.manager["custom-dev-name", "usb"]
        self.assertNotIn("custom-dev-name", self.manager,
                         msg="Deleting an item of DeviceManager failed")

        with self.assertRaises(KeyError, msg="Should not be able to remove the same key twice"):
            del self.manager["custom-dev-name"]
        with self.assertRaises(TypeError, msg="Invalid argument type"):
            self.manager.find_by_device(123)

        self.manager.clear()
        self.assertEqual(0, len(self.manager), msg="DeviceManager must be empty after clearing it")

    def test_finding_devices(self):
        self.manager.scanner[DeviceType.USB].mock_scan.reset_mock()
        self.manager.scanner[DeviceType.LAN].mock_scan.reset_mock()
        self.manager["my-dev-0", "usb"] = self.usb_devices[0].address
        self.manager.scanner[DeviceType.LAN].mock_scan.assert_not_called()
        self.manager.scanner[DeviceType.USB].mock_scan.assert_called_once_with(False)

        self.manager.scanner[DeviceType.USB].mock_scan.reset_mock()
        self.manager.scanner[DeviceType.LAN].mock_scan.reset_mock()
        self.manager["my-dev-0", "lan"] = self.lan_devices[0].address
        self.manager.scanner[DeviceType.USB].mock_scan.assert_not_called()
        self.manager.scanner[DeviceType.LAN].mock_scan.assert_called_once_with(False)

        self.manager.scanner[DeviceType.USB].mock_scan.reset_mock()
        self.manager.scanner[DeviceType.LAN].mock_scan.reset_mock()
        with self.assertRaises(ValueError,
                               msg="If address was not found, DeviceManager must raise an error"):
            self.manager["my-dev-1"] = "invalid-address"
        self.manager.scanner[DeviceType.USB].mock_scan.assert_has_calls([unittest.mock.call(False), unittest.mock.call(True)])
        self.manager.scanner[DeviceType.LAN].mock_scan.assert_has_calls([unittest.mock.call(False), unittest.mock.call(True)])

        tmp_dev = self.usb_devices[1]
        self.manager["my-dev-2"] = self.make_usb_device(None, tmp_dev.vendor_id, tmp_dev.product_id,
                                                        tmp_dev.revision_id, tmp_dev.serial)
        self.assertEqual(tmp_dev, self.manager["my-dev-2"],
                         msg="DeviceManager should check/update addresses of new usb device")
        tmp_dev = self.lan_devices[1]
        self.manager["my-dev-3"] = self.make_lan_device(None, tmp_dev.mac_address)
        self.assertEqual(tmp_dev, self.manager["my-dev-3"],
                         msg="DeviceManager should check/update addresses of new lan device")
        tmp_dev = self.make_usb_device("usb37\\test", 1, 2, 3, "1234BCAD", aliases=["ab", "cd"])
        self.manager.set("my-dev-4", tmp_dev, scan=True)
        self.assertSequenceEqual(tuple(), self.manager["my-dev-4"].all_addresses,
                                 msg="If a new device was not found, the addresses must be reset")

        self.manager.scanner[DeviceType.USB].mock_scan.reset_mock()
        self.manager.scanner[DeviceType.LAN].mock_scan.reset_mock()
        old_usb_device = self.usb_devices.pop(0)
        old_lan_device = self.lan_devices.pop(0)

        device = self.manager.get(("my-dev-0", "usb"), scan=True)
        self.manager.scanner[DeviceType.LAN].mock_scan.assert_not_called()
        self.manager.scanner[DeviceType.USB].mock_scan.assert_called_once_with(True)
        self.assertSequenceEqual(tuple(), device.all_addresses, msg="All addresses need to be "
                                 "reset after finding out it was disconnected")

        self.manager.scanner[DeviceType.LAN].mock_scan.reset_mock()
        self.manager.scanner[DeviceType.USB].mock_scan.reset_mock()

        devices = self.manager.get("my-dev-0", scan=True)
        self.manager.scanner[DeviceType.USB].mock_scan.assert_called_once_with(True)
        self.manager.scanner[DeviceType.LAN].mock_scan.assert_called_once_with(True)
        for device in devices.values():
            self.assertSequenceEqual(tuple(), device.all_addresses, msg="All addresses need to be "
                                     "reset after finding out it was disconnected")

        self.usb_devices.insert(0, old_usb_device)
        self.lan_devices.insert(0, old_lan_device)

        self.manager.reset_addresses()
        for devices in self.manager.values():
            for device in devices.values():
                self.assertSequenceEqual(tuple(), device.all_addresses, msg="Addresses were still"
                                         "found after calling DeviceManager.reset_addresses")

        self.assertEqual(4, len(self.manager), msg="Unexpected length of DeviceManager")
        self.manager.clear()
        self.assertEqual(0, len(self.manager), msg="DeviceManager must be empty after clearing it")

    def test_serialization(self):
        import tempfile

        device_key = "dev-{}"
        for i, usb_device in enumerate(self.usb_devices[:2]):
            self.manager[device_key.format(i)] = usb_device.address
        for i, lan_device in enumerate(self.lan_devices[:3]):
            self.manager[device_key.format(i)] = lan_device.address

        with self.mock_device_scanner():
            new_manager = DeviceManager()

        with tempfile.TemporaryDirectory() as dir_name:
            print(dir_name)
            file_name = os.path.join(dir_name, "testfile.json")
            with open(file_name, "w") as file:
                self.manager.save(file)

            with self.mock_device_scanner():
                with load_device_manager(file_name, autosave=True) as file_manager:
                    self.assertEqual(len(self.manager), len(file_manager),
                                     msg="DeviceManager was not saved and loaded correctly")
                    self.assertSequenceEqual(self.manager.items(), file_manager.items(),
                                             msg="DeviceManager was not saved and loaded correctly")
                    file_manager["new-dev-abc"] = self.usb_devices[-1].address

                with load_device_manager(file_name) as new_file_manager:
                    self.assertEqual(len(file_manager), len(new_file_manager),
                                     msg="DeviceManager was not saved and loaded correctly")
                    self.assertSequenceEqual(file_manager.items(), new_file_manager.items(),
                                             msg="DeviceManager was not saved and loaded correctly")


if __name__ == "__main__":
    unittest.main()
