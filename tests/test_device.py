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
import typing
import unittest

from device_manager.device import *


class TestDeviceType(unittest.TestCase):
    class DummyDevice(Device):
        @property
        def device_type(self) -> DeviceType:
            return DeviceType.USB if self.address is not None else None

        @property
        def unique_identifier(self) -> typing.Dict[str, typing.Any]:
            return dict()

    def setUp(self) -> None:
        self.device_type_mapping = {DeviceType.USB: USBDevice,
                                    DeviceType.LAN: LANDevice}

    def try_make_device_type(self, expected, from_obj) -> None:
        try:
            device_type = DeviceType(from_obj)
        except:
            self.fail(msg="Could not create DeviceType from {}".format(type(from_obj)))
        self.assertEqual(device_type, expected,
                         msg="Invalid DeviceType was created from {}".format(type(from_obj)))

    def test_enum_members(self) -> None:
        self.assertSetEqual(set(DeviceType), set([DeviceType.USB, DeviceType.LAN]),
                            msg="Not all DeviceType-members are covered by the test.")

        for device_type_enum, device_type in self.device_type_mapping.items():
            self.assertEqual(device_type_enum.type, device_type,
                             msg="DeviceType.type does not match the corresponding Device-type")

    def test_constructor(self) -> None:
        for device_type_enum, device_type in self.device_type_mapping.items():
            self.try_make_device_type(device_type_enum, device_type_enum)
            self.try_make_device_type(device_type_enum, device_type_enum.value)
            self.try_make_device_type(device_type_enum, device_type_enum.value.lower())
            self.try_make_device_type(device_type_enum, device_type_enum.value.upper())
            self.try_make_device_type(device_type_enum, device_type)
            self.try_make_device_type(device_type_enum, device_type())

        with self.assertRaises(ValueError):
            device_type = DeviceType(123)
        with self.assertRaises(ValueError):
            device_type = DeviceType("invalid")
        with self.assertRaises(ValueError):
            device_type = DeviceType(self.DummyDevice)


class TestDevice(unittest.TestCase):
    class DummyDevice(Device):
        @property
        def device_type(self) -> DeviceType:
            return super().device_type

        @property
        def unique_identifier(self) -> typing.Dict[str, typing.Any]:
            return super().unique_identifier

    def test_abstract_attributes(self):
        dummy_device = self.DummyDevice()

        with self.assertRaises(NotImplementedError,
                               msg="Device.device_type should not be implemented."):
            tmp = dummy_device.device_type
        with self.assertRaises(NotImplementedError,
                               msg="Device.unique_identifier should not be implemented."):
            tmp = dummy_device.unique_identifier

    def test_attributes(self):
        dummy_device = self.DummyDevice()

        self.assertIsNone(dummy_device.address,
                          msg="Initially Device.address must be None")
        self.assertEqual(len(dummy_device.address_aliases), 0,
                         msg="Initially Device.address_aliases must be empty")
        self.assertEqual(len(dummy_device.all_addresses), 0,
                         msg="Initially Device.all_addresses must be empty")

        tmp_address = "test-address"
        dummy_device.address = tmp_address
        self.assertEqual(dummy_device.address, tmp_address,
                         msg="Device.address was not set to the expected value")
        tmp_address_aliases = ["addr0", "addr1", "addr2"]
        dummy_device.address_aliases = tmp_address_aliases
        self.assertEqual(dummy_device.address_aliases, tuple(tmp_address_aliases),
                         msg="Device.address_aliases was not set to the expected value")
        tmp_all_addresses = [tmp_address, *tmp_address_aliases]
        self.assertSequenceEqual(dummy_device.all_addresses, tuple(tmp_all_addresses),
                                 msg="Device.all_addresses does not contain the expected values")


class TestUSBDevice(unittest.TestCase):
    def setUp(self):
        self.test_device = USBDevice()

        tmp_vendor_id = 0x1122
        tmp_product_id = 0xABAB
        tmp_revision_id = 0x8888
        tmp_serial = "AB1234CD"
        tmp_address = "USB0\\testdevice"
        tmp_address_aliases = ["USB0\\AAA", "USB0\\BBB"]

        self.test_device.vendor_id = tmp_vendor_id
        self.test_device.product_id = tmp_product_id
        self.test_device.revision_id = tmp_revision_id
        self.test_device.serial = tmp_serial
        self.test_device.address = tmp_address
        self.test_device.address_aliases = tmp_address_aliases

        self.expected_dict = dict(type="usb",
                                  address=tmp_address,
                                  address_aliases=tmp_address_aliases,
                                  vendor_id=tmp_vendor_id,
                                  product_id=tmp_product_id,
                                  revision_id=tmp_revision_id,
                                  serial=tmp_serial)

    def test_attributes(self):
        device = USBDevice()

        self.assertEqual(device.device_type, DeviceType.USB,
                         msg="Initially USBDevice.device_type must be DeviceType.USB")
        tmp_uid = dict(vendor_id=None, product_id=None, serial=None)
        self.assertDictEqual(device.unique_identifier, tmp_uid,
                             msg="Initially USBDevice.unique_identifier must be {}".format(tmp_uid))
        self.assertIsNone(device.vendor_id,
                          msg="Initially USBDevice.vendor_id must be None")
        self.assertIsNone(device.product_id,
                          msg="Initially USBDevice.product_id must be None")
        self.assertIsNone(device.revision_id,
                          msg="Initially USBDevice.revision_id must be None")
        self.assertIsNone(device.serial,
                          msg="Initially USBDevice.serial must be None")

        tmp_vendor_id = 0x1234
        device.vendor_id = tmp_vendor_id
        self.assertEqual(device.vendor_id, tmp_vendor_id,
                         msg="USBDevice.vendor_id was not set to the expected value")
        tmp_product_id = 0xABCD
        device.product_id = tmp_product_id
        self.assertEqual(device.product_id, tmp_product_id,
                         msg="USBDevice.product_id was not set to the expected value")
        tmp_revision_id = 0x0100
        device.revision_id = tmp_revision_id
        self.assertEqual(device.revision_id, tmp_revision_id,
                         msg="USBDevice.revision_id was not set to the expected value")
        tmp_serial = "1234567890AB"
        device.serial = tmp_serial
        self.assertEqual(device.serial, tmp_serial,
                         msg="USBDevice.serial was not set to the expected value")

        tmp_uid = dict(vendor_id=tmp_vendor_id, product_id=tmp_product_id, serial=tmp_serial)
        self.assertDictEqual(device.unique_identifier, tmp_uid,
                             msg="USBDevice.unique_identifier does not contain the expected values")

    def test_comparison(self):
        device = USBDevice()

        self.assertNotEqual(device, self.test_device, msg="USBDevices should be unequal")

        device.from_device(self.test_device)
        self.assertEqual(device, self.test_device,
                         msg="USBDevices should be equal after calling from_device")

        device.reset_addresses()
        self.assertIsNone(device.address,
                          msg="USBDevice.address must be None after calling reset_addresses")
        self.assertSequenceEqual(device.address_aliases, tuple(),
                                 msg="USBDevice.address_aliases must be empty after calling "
                                     "reset_addresses")
        self.assertSequenceEqual(device.all_addresses, tuple(),
                                 msg="USBDevice.all_addresses must be empty after calling "
                                     "reset_addresses")

        self.assertListEqual(list(self.test_device.all_addresses), device._old_addresses,
                             msg="USBDevice._old_address must contain the addresses that were in "
                                 "all_addresses before calling reset_addresses")
        self.assertEqual(device, self.test_device,
                         msg="USBDevices should be equal, if their unique identifiers are equal")

    def test_serialization(self):
        device = USBDevice()

        device_dict = self.test_device.to_dict()
        self.assertDictEqual(device_dict, self.expected_dict,
                             msg="Device.to_dict returned an invalid dictionary")

        device.from_dict(device_dict)
        self.assertEqual(device, self.test_device,
                         msg="Devices must be equal after serialization and deserialization")
        self.assertDictEqual(device.to_dict(), device_dict,
                             msg="A deserialized Device should return the same serialized "
                                 "dictionary")

        device.from_dict(device_dict, old=True)
        self.assertEqual(device, self.test_device,
                         msg="Devices must be equal after serialization and deserialization")
        self.assertNotEqual(device.to_dict(), device_dict,
                            msg="A deserialized Device should return another serialized "
                                "dictionary if it was deserialized with old addresses")
        self.assertListEqual(device._old_addresses, list(self.test_device.all_addresses),
                             msg="After deserializing a Device with old addresses, the addresses "
                                 "should appear in _old_addresses")


class TestLANDevice(unittest.TestCase):
    pass


if __name__ == "__main__":
    unittest.main()
