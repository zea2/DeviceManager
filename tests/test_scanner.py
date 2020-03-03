#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script for testing the module device_manager.device.

This script tests the following entities:
- class USBDeviceScanner
- class LANDeviceScanner (including BaseLANDeviceScanner, NMAPWrapper)
- class DeviceScanner
- (indirectly: abstract class BaseDeviceScanner)

Authors:
    Lukas Lankes, Forschungszentrum Jülich GmbH - ZEA-2, l.lankes@fz-juelich.de
"""

import unittest


class TestUSBDeviceScanner(unittest.TestCase):
    pass


class TestLANDeviceScanner(unittest.TestCase):
    pass


class TestGeneralDeviceScanner(unittest.TestCase):
    pass


if __name__ == "__main__":
    unittest.main()
