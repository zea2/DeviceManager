#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script for testing the module device_manager.device.

This script tests the following entities:
- enumeration class DeviceType
- class USBDevice
- class LANDevice
- abstract class Device

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
        self.assertEqual(expected, device_type,
                         msg="Invalid DeviceType was created from {}".format(type(from_obj)))

    def test_enum_members(self) -> None:
        self.assertSetEqual(set([DeviceType.USB, DeviceType.LAN]), set(DeviceType),
                            msg="Not all DeviceType-members are covered by the test.")

        for device_type_enum, device_type in self.device_type_mapping.items():
            self.assertEqual(device_type, device_type_enum.type,
                             msg="DeviceType.type does not match the corresponding Device-type")

    def test_constructor(self) -> None:
        for device_type_enum, device_type in self.device_type_mapping.items():
            self.try_make_device_type(device_type_enum, device_type_enum)
            self.try_make_device_type(device_type_enum, device_type_enum.value)
            self.try_make_device_type(device_type_enum, device_type_enum.value.lower())
            self.try_make_device_type(device_type_enum, device_type_enum.value.upper())
            self.try_make_device_type(device_type_enum, device_type)
            self.try_make_device_type(device_type_enum, device_type())

        with self.assertRaises(ValueError, msg="Using an invalid type to create a DeviceType-"
                                               "object should raise an exception"):
            device_type = DeviceType(123)
        with self.assertRaises(ValueError, msg="Using an invalid string to create a DeviceType-"
                                               "object should raise an exception"):
            device_type = DeviceType("invalid")
        with self.assertRaises(ValueError, msg="Using an unknown device-type to create a "
                                               "DeviceType-object should raise an exception"):
            device_type = DeviceType(self.DummyDevice)


class TestDevice(unittest.TestCase):
    class MockDevice(Device):
        @property
        def device_type(self) -> DeviceType:
            return super().device_type

        @property
        def unique_identifier(self) -> typing.Dict[str, typing.Any]:
            return super().unique_identifier

    def test_attributes(self):
        dummy_device = self.MockDevice()

        self.assertIsNone(dummy_device.address,
                          msg="Initially Device.address must be None")
        self.assertEqual(0, len(dummy_device.address_aliases),
                         msg="Initially Device.address_aliases must be empty")
        self.assertEqual(0, len(dummy_device.all_addresses),
                         msg="Initially Device.all_addresses must be empty")

        tmp_address = "test-address"
        dummy_device.address = tmp_address
        self.assertEqual(tmp_address, dummy_device.address,
                         msg="Device.address was not set to the expected value")
        tmp_address_aliases = ["addr0", "addr1", "addr2"]
        dummy_device.address_aliases = [None, *tmp_address_aliases, None]
        self.assertEqual(tuple(tmp_address_aliases), dummy_device.address_aliases,
                         msg="Device.address_aliases was not set to the expected value")
        tmp_all_addresses = [tmp_address, *tmp_address_aliases]
        self.assertSequenceEqual(tuple(tmp_all_addresses), dummy_device.all_addresses,
                                 msg="Device.all_addresses does not contain the expected values")
        dummy_device.address_aliases = None
        self.assertSequenceEqual(tuple(), dummy_device.address_aliases,
                                 msg="Setting Device.address_aliases to None should set it to an "
                                     "empty tuple")
        tmp_address_aliases = "addr0"
        dummy_device.address_aliases = tmp_address_aliases
        self.assertSequenceEqual((tmp_address_aliases,), dummy_device.address_aliases,
                                 msg="Setting Device.address_aliases to a string should "
                                     "automatically wrap the string into a tuple")

        with self.assertRaises(TypeError, msg="Using an invalid type to set as Device.address "
                                              "should raise an exception"):
            dummy_device.address = 123
        with self.assertRaises(TypeError, msg="Using an invalid type to set as item of "
                                              "Device.address_aliases should raise an exception"):
            dummy_device.address_aliases = ["abc", 123]


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

        self.assertEqual(DeviceType.USB, device.device_type,
                         msg="Initially USBDevice.device_type must be DeviceType.USB")
        tmp_uid = dict(vendor_id=None, product_id=None, serial=None)
        self.assertDictEqual(tmp_uid, device.unique_identifier,
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
        self.assertEqual(tmp_vendor_id, device.vendor_id,
                         msg="USBDevice.vendor_id was not set to the expected value")
        tmp_product_id = 0xABCD
        device.product_id = tmp_product_id
        self.assertEqual(tmp_product_id, device.product_id,
                         msg="USBDevice.product_id was not set to the expected value")
        tmp_revision_id = 0x0100
        device.revision_id = tmp_revision_id
        self.assertEqual(tmp_revision_id, device.revision_id,
                         msg="USBDevice.revision_id was not set to the expected value")
        tmp_serial = "1234567890AB"
        device.serial = tmp_serial
        self.assertEqual(tmp_serial, device.serial,
                         msg="USBDevice.serial was not set to the expected value")

        tmp_uid = dict(vendor_id=tmp_vendor_id, product_id=tmp_product_id, serial=tmp_serial)
        self.assertDictEqual(tmp_uid, device.unique_identifier,
                             msg="USBDevice.unique_identifier does not contain the expected values")

        with self.assertRaises(TypeError, msg="Setting USBDevice.vendor_id to an invalid type "
                                              "should raise an exception"):
            device.vendor_id = "abc"
        with self.assertRaises(TypeError, msg="Setting USBDevice.product_id to an invalid type "
                                              "should raise an exception"):
            device.product_id = "abc"
        with self.assertRaises(TypeError, msg="Setting USBDevice.revision_id to an invalid type "
                                              "should raise an exception"):
            device.revision_id = "abc"
        with self.assertRaises(TypeError, msg="Setting USBDevice.serial to an invalid type should "
                                              "raise an exception"):
            device.serial = 123.456

    def test_comparison(self):
        device = USBDevice()

        self.assertNotEqual(self.test_device, device, msg="USBDevices should be unequal")

        device.from_device(self.test_device)
        self.assertEqual(self.test_device, device,
                         msg="USBDevices should be equal after calling from_device")

        device.reset_addresses()
        self.assertIsNone(device.address,
                          msg="USBDevice.address must be None after calling reset_addresses")
        self.assertSequenceEqual(tuple(), device.address_aliases,
                                 msg="USBDevice.address_aliases must be empty after calling "
                                     "reset_addresses")
        self.assertSequenceEqual(tuple(), device.all_addresses,
                                 msg="USBDevice.all_addresses must be empty after calling "
                                     "reset_addresses")

        self.assertListEqual(list(self.test_device.all_addresses), device._old_addresses,
                             msg="USBDevice._old_address must contain the addresses that were in "
                                 "all_addresses before calling reset_addresses")
        self.assertNotEqual(self.test_device, device,
                            msg="USBDevices should be unequal after resetting addresses")
        self.assertEqual(self.test_device.unique_identifier, device.unique_identifier,
                         msg="unique_identifiers of USBDevices should still be equal after "
                             "resetting addresses")

        with self.assertRaises(TypeError, msg="The attribute of Device.from_device needs to have "
                                              "the same type as self"):
            device.from_device(LANDevice())

    def test_serialization(self):
        device = USBDevice()

        device_dict = self.test_device.to_dict()
        self.assertDictEqual(self.expected_dict, device_dict,
                             msg="Device.to_dict returned an invalid dictionary")

        device.from_dict(device_dict)
        self.assertEqual(self.test_device, device,
                         msg="Devices must be equal after serialization and deserialization")
        self.assertDictEqual(device_dict, device.to_dict(),
                             msg="A deserialized Device should return the same serialized "
                                 "dictionary")

        device.from_dict(device_dict, old=True)
        self.assertNotEqual(self.test_device, device,
                            msg="Devices must be unequal after serialization and deserialization "
                                "with old addresses")
        self.assertNotEqual(device_dict, device.to_dict(),
                            msg="A deserialized Device should return another serialized "
                                "dictionary if it was deserialized with old addresses")
        self.assertListEqual(device._old_addresses, list(self.test_device.all_addresses),
                             msg="After deserializing a Device with old addresses, the addresses "
                                 "should appear in _old_addresses")


class TestLANDevice(unittest.TestCase):
    def setUp(self):
        self.test_device = LANDevice()

        tmp_mac_address = "12:34:56:78:90:AB"
        tmp_address = "192.168.1.2"
        tmp_address_aliases = ["192.168.1.20", "123.45.67.89"]

        self.test_device.mac_address = tmp_mac_address
        self.test_device.address = tmp_address
        self.test_device.address_aliases = tmp_address_aliases

        self.expected_dict = dict(type="lan",
                                  address=tmp_address,
                                  address_aliases=tmp_address_aliases,
                                  mac_address=tmp_mac_address)

    def test_attributes(self):
        device = LANDevice()

        self.assertEqual(DeviceType.LAN, device.device_type,
                         msg="Initially LANDevice.device_type must be DeviceType.USB")
        tmp_uid = dict(mac_address=None)
        self.assertDictEqual(tmp_uid, device.unique_identifier,
                             msg="Initially LANDevice.unique_identifier must be {}".format(tmp_uid))
        self.assertIsNone(device.mac_address,
                          msg="Initially LANDevice.mac_address must be None")

        tmp_mac_address = "11:22:33:44:55:66"
        device.mac_address = tmp_mac_address
        self.assertEqual(tmp_mac_address, device.mac_address,
                         msg="LANDevice.mac_address was not set to the expected value")
        device.mac_address = None
        self.assertIsNone(device.mac_address,
                          msg="LANDevice.mac_address was not set to None")
        device.mac_address = tmp_mac_address.replace(":", ".")
        self.assertEqual(tmp_mac_address, device.mac_address,
                         msg="LANDevice.mac_address was not set to the expected value")
        device.mac_address = tmp_mac_address.replace(":", "-")
        self.assertEqual(tmp_mac_address, device.mac_address,
                         msg="LANDevice.mac_address was not set to the expected value")

        tmp_uid = dict(mac_address=tmp_mac_address)
        self.assertDictEqual(tmp_uid, device.unique_identifier,
                             msg="LANDevice.unique_identifier does not contain the expected values")

        with self.assertRaises(TypeError, msg="Setting LANDevice.mac_address to an invalid type "
                                              "should raise an exception"):
            device.mac_address = 1234
        with self.assertRaises(TypeError, msg="Setting LANDevice.mac_address to an invalid "
                                              "formatted string should raise an exception"):
            device.mac_address = "1234567890AB"

    def test_comparison(self):
        device = LANDevice()

        self.assertNotEqual(self.test_device, device, msg="LANDevices should be unequal")

        device.from_device(self.test_device)
        self.assertEqual(device, self.test_device,
                         msg="LANDevices should be equal after calling from_device")

        device.reset_addresses()
        self.assertIsNone(device.address,
                          msg="LANDevice.address must be None after calling reset_addresses")
        self.assertSequenceEqual(tuple(), device.address_aliases,
                                 msg="LANDevice.address_aliases must be empty after calling "
                                     "reset_addresses")
        self.assertSequenceEqual(tuple(), device.all_addresses,
                                 msg="LANDevice.all_addresses must be empty after calling "
                                     "reset_addresses")

        self.assertListEqual(list(self.test_device.all_addresses), device._old_addresses,
                             msg="LANDevice._old_address must contain the addresses that were in "
                                 "all_addresses before calling reset_addresses")
        self.assertNotEqual(self.test_device, device,
                            msg="LANDevices should be unequal after resetting addresses")
        self.assertEqual(self.test_device.unique_identifier, device.unique_identifier,
                         msg="unique_identifiers of LANDevices should still be equal after "
                             "resetting addresses")

        with self.assertRaises(TypeError, msg="The attribute of Device.from_device needs to have "
                                              "the same type as self"):
            device.from_device(USBDevice())

    def test_serialization(self):
        device = LANDevice()

        device_dict = self.test_device.to_dict()
        self.assertDictEqual(self.expected_dict, device_dict,
                             msg="Device.to_dict returned an invalid dictionary")

        device.from_dict(device_dict)
        self.assertEqual(self.test_device, device,
                         msg="Devices must be equal after serialization and deserialization")
        self.assertDictEqual(device_dict, device.to_dict(),
                             msg="A deserialized Device should return the same serialized "
                                 "dictionary")

        device.from_dict(device_dict, old=True)
        self.assertNotEqual(self.test_device, device,
                            msg="Devices must be equal after serialization and deserialization "
                                "with old addresses")
        self.assertNotEqual(device_dict, device.to_dict(),
                            msg="A deserialized Device should return another serialized "
                                "dictionary if it was deserialized with old addresses")
        self.assertListEqual(list(self.test_device.all_addresses), device._old_addresses,
                             msg="After deserializing a Device with old addresses, the addresses "
                                 "should appear in _old_addresses")


if __name__ == "__main__":
    unittest.main()
