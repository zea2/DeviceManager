#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script for testing the module device_manager.device.

This script tests the following entities:
- enumeration class DeviceType
- class USBDevice
- class LANDevice
- (indirectly: abstract class Device)

Authors:
    Lukas Lankes, Forschungszentrum Jülich GmbH - ZEA-2, l.lankes@fz-juelich.de
"""

import unittest


class TestDeviceType(unittest.TestCase):
    pass


class TestUSBDevice(unittest.TestCase):
    pass


class TestLANDevice(unittest.TestCase):
    pass


if __name__ == "__main__":
    unittest.main()
