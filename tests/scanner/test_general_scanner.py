#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script for testing the module device_manager.scanner._win32.

This script tests the following entities:
- class DeviceScanner

Authors:
    Lukas Lankes, Forschungszentrum Jülich GmbH - ZEA-2, l.lankes@fz-juelich.de
"""

import unittest
import unittest.mock

from device_manager.device import USBDevice, LANDevice, DeviceType
from device_manager.scanner import DeviceScanner, USBDeviceScanner, LANDeviceScanner


class TestGeneralDeviceScanner(unittest.TestCase):
    def setUp(self) -> None:
        self.device_types = [DeviceType.USB, DeviceType.LAN]
        self.scanner = DeviceScanner()

        self.scan_mock = {}
        for device_type in self.device_types:
            self.scan_mock[device_type] = unittest.mock.MagicMock()
            self.scanner[device_type]._scan = self.scan_mock[device_type]

    def test_scan(self):
        for device_type in self.scanner:
            self.assertIn(device_type, self.device_types, msg="Unexpected scanner type")
        for device_type in self.device_types:
            self.assertIn(device_type.value, self.scanner, msg="Unexpected scanner type")

        self.scanner.list_devices(rescan=True)
        for device_type in self.device_types:
            self.scan_mock[device_type].assert_called_once_with(True)

        self.assertIn(None, self.scanner,
                      msg="DeviceScanner.scanners should contain None")
        self.assertIs(self.scanner, self.scanner[None],
                      msg="DeviceScanner.scanners[None] should return the self-object")
