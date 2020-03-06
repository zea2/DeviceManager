#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script for testing the module device_manager.scanner._linux.

This script tests the following entities:
- class LinuxUSBDeviceScanner
- class LinuxLANDeviceScanner

Authors:
    Lukas Lankes, Forschungszentrum Jülich GmbH - ZEA-2, l.lankes@fz-juelich.de
"""

import subprocess
import sys
import unittest
import unittest.mock

from device_manager.device import USBDevice, LANDevice
from device_manager.scanner import USBDeviceScanner, LANDeviceScanner


@unittest.skipUnless(sys.platform != "win32", "Requires Linux")
class TestLinuxScannerImport(unittest.TestCase):
    def test_import(self):
        from device_manager.scanner._linux import LinuxUSBDeviceScanner, LinuxLANDeviceScanner

        self.assertIs(USBDeviceScanner, LinuxUSBDeviceScanner)
        self.assertIs(LANDeviceScanner, LinuxLANDeviceScanner)

    def test_import_error(self):
        with self.assertRaises(ImportError, msg="Importing windows-specific device scanners should "
                                                "fail on linux"):
            import device_manager.scanner._win32


@unittest.skipUnless(sys.platform != "win32", "Requires Linux")
class TestLinuxUSBDeviceScanner(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def test_scan(self):
        pass

    def test_scan_errors(self):
        pass


@unittest.skipUnless(sys.platform != "win32", "Requires Linux")
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
        pass

    def test_scan(self):
        pass

    def test_scan_errors(self):
        pass
