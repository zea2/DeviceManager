#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Device types that are supported by the device manager and scanners.

Currently two types of devices are supported: USB and LAN devices. USB devices are identified by
their vendor id, product id and serial number. The ethernet (LAN) devices use their mac address for
a unique identification. Device's are simple data classes that store the relevant information of the
device. They are abstracted by their abstract base class `Device`. The device types are also
encapsulated by the `DeviceType` enumeration. This enumeration makes it easier to find out the
device's type and to specify requested types when using scanners or the device manager.
"""

import abc
import enum
import re
import typing
from device_manager.utils.usb_vendor_database import USBVendorDatabase

__all__ = ["DeviceType", "Device", "USBDevice", "LANDevice"]

####################################################################################################


class DeviceType(enum.Enum):
    """An enumeration of available device types."""

    USB = "usb"
    LAN = "lan"

    @property
    def type(self) -> typing.Type["Device"]:
        """Returns the corresponding device type.

        Returns:
            type: Corresponding `Device`-type of this enumeration value.
        """
        if self.value == self.USB.value:
            return USBDevice
        elif self.value == self.LAN.value:
            return LANDevice
        # Unknown device type
        raise ValueError("Invalid DeviceType: {}".format(self.value))  # pragma: no cover

    @classmethod
    def _missing_(cls, value: "DeviceTypeType") -> "DeviceType":
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
            for member in cls:
                if member.name.lower() == value.lower():
                    return member  # pragma: no cover
        elif isinstance(value, Device):
            return value.device_type
        elif isinstance(value, type) and issubclass(value, Device):
            try:
                # The property should return a constant value, so `self` is not required
                device_type = value.device_type.fget(None)
            except AttributeError:
                # If it is not working, create an instance, to get the corresponding DeviceType
                device_type = value().device_type
            if device_type is not None and device_type.type is value:
                return device_type
        return super()._missing_(value)


class Device(abc.ABC):
    """Base class for all supported device types."""

    def __init__(self):
        super().__init__()
        self._address = None
        self._address_aliases = []
        self._old_addresses = []

    @property
    @abc.abstractmethod
    def device_type(self) -> DeviceType:
        """Corresponding `DeviceType`-object"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def unique_identifier(self) -> typing.Dict[str, typing.Any]:
        """Returns an unique identifier for this device. This makes device objects of the same or
        similar type comparable.
        """
        raise NotImplementedError()

    @property
    def address(self) -> typing.Optional[str]:
        """Main address of the device."""
        return self._address

    @address.setter
    def address(self, address: typing.Optional[str]) -> None:
        if not isinstance(address, (str, type(None))):
            raise TypeError("address")
        self._address = address

    @property
    def address_aliases(self) -> typing.Sequence[str]:
        """Address aliases for this device.

        If there are more than one address, which can be used to connect to the device, these
        addresses can be found here. If there is only one this property remains empty.
        """
        return tuple(self._address_aliases)

    @address_aliases.setter
    def address_aliases(self, address_aliases: typing.Optional[typing.Iterable[str]]) -> None:
        if address_aliases is None:
            # None is interpreted as empty list
            self._address_aliases = []
        elif isinstance(address_aliases, str):
            # Convert a single string into a list
            self._address_aliases = [address_aliases]
        else:
            try:
                self._address_aliases = []
                for i, address in enumerate(address_aliases):
                    if address is None:
                        continue  # Ignore None-values
                    if not isinstance(address, str):
                        raise TypeError(f"address_aliases[{i}]")
                    self._address_aliases.append(address)
            except TypeError as exc:
                # The value to set was not a string-Iterable.
                raise TypeError("address_aliases") from exc

    @property
    def all_addresses(self) -> typing.Sequence[str]:
        """All addresses contained in properties address and address_aliases"""
        if self.address is None:
            # If `address` is None, the first value of the returned list should not be None.
            return self.address_aliases
        return tuple([self.address, *self.address_aliases])

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        """Converts the object into a dictionary.

        Subclasses should call super.to_dict, when overriding this function.

        Returns:
            dict: Device object represented as dictionary.
        """
        return {"type": self.device_type.value,
                "address": self.address,
                "address_aliases": list(self.address_aliases)}

    def from_dict(self, dct: typing.Dict[str, typing.Any], old: bool = False) -> None:
        """Fills the attributes from a dictionary.

        Subclasses should call super.from_dict, when overriding this function.

        Args:
            dct: A dictionary containing values, used to fill these object's attributes.
            old: True, if the addresses in `d` should be set as `_old_addresses` because they are
                 not upt-to-date. False (default), if the addresses should be set to these values.
        """
        self.address = dct["address"] if "address" in dct else None
        self.address_aliases = dct["address_aliases"] if "address_aliases" in dct else None
        if old:
            self.reset_addresses()

    def from_device(self, other: "Device") -> None:
        """Updates self from another device.

        Addresses that are currently in `address` or `address_aliases`, will be moved to
        `_old_addresses`.

        Args:
            other: Device that is used to update self.
        """
        if other is self:
            # If the other object is the same as this, There is nothing to do
            return  # pragma: no cover
        if not isinstance(other, type(self)):
            raise TypeError("other")
        self.reset_addresses()
        self.address = other.address
        self.address_aliases = other.address_aliases
        # Move all old addresses to `_old_addresses`, that are not already in `all_addresses`. The
        # old addresses are converted into a set, so there are no duplicates.
        self._old_addresses = [address for address in {*self._old_addresses, *other._old_addresses}
                               if address not in self.all_addresses]

    def __repr__(self) -> str:
        """String-representation of the device.

        Returns:
            str: String-representation of this object.
        """
        return "{}({})".format(type(self).__name__, repr(self.address))

    def __eq__(self, other: "Device") -> bool:
        """Compares this device object with another by comparing their `unique_identifier`s.

        Args:
            other: Other device object to compare with this one.

        Returns:
            bool: True, if the objects are equal, otherwise False.
        """
        if type(other) != type(self):
            # Compare types instead of using isinstance, because both objects must to be the same
            # and so must their types
            return False
        return set(self.all_addresses) == set(other.all_addresses)

    def reset_addresses(self) -> None:
        """Moves `address` and `address_aliases` to `_old_addresses`."""
        for address in self.all_addresses:
            if address not in self._old_addresses:
                self._old_addresses.append(address)
        self.address = None
        self.address_aliases = []


class USBDevice(Device):
    """Special device class for USB devices."""

    def __init__(self):
        super().__init__()
        self._vendor_id = None
        self._product_id = None
        self._revision_id = None
        self._serial = None
        self._vendor_name = None
        self._product_name = None

    @property
    def device_type(self) -> DeviceType:
        """Corresponding `DeviceType`-object."""
        return DeviceType.USB

    @property
    def unique_identifier(self) -> typing.Dict[str, typing.Any]:
        """Returns an unique identifier for this device. This makes device objects of the same or
        similar type comparable.

        The unique identifiers of an usb device are `vendor_id`, `product_id` and `serial`.
        """
        return dict(vendor_id=self.vendor_id,
                    product_id=self.product_id,
                    serial=self.serial)

    @property
    def vendor_id(self) -> typing.Optional[int]:
        """Manufacturer id of the USB device, defined by the USB committee."""
        return self._vendor_id

    @vendor_id.setter
    def vendor_id(self, vendor_id: typing.Optional[int]) -> None:
        if not isinstance(vendor_id, (int, type(None))):
            raise TypeError("vendor_id")
        self._vendor_id = vendor_id
        self._vendor_name, self._product_name = USBVendorDatabase.get_vendor_product_name(
                                                    self.vendor_id, self.product_id)

    @property
    def vendor_name(self) -> str:
        """Name of the device's manufacturer."""
        return self._vendor_name

    @property
    def product_id(self) -> typing.Optional[int]:
        """Product id of the USB device, defined by the manufacturer."""
        return self._product_id

    @product_id.setter
    def product_id(self, product_id: typing.Optional[int]) -> None:
        if not isinstance(product_id, (int, type(None))):
            raise TypeError("product_id")
        self._product_id = product_id
        self._vendor_name, self._product_name = USBVendorDatabase.get_vendor_product_name(
                                                    self.vendor_id, self.product_id)

    @property
    def product_name(self) -> str:
        """The model name of the device."""
        return self._product_name

    @property
    def revision_id(self) -> typing.Optional[int]:
        """Revisision code of the USB device."""
        return self._revision_id

    @revision_id.setter
    def revision_id(self, revision_id: typing.Optional[int]) -> None:
        if not isinstance(revision_id, (int, type(None))):
            raise TypeError("revision_id")
        self._revision_id = revision_id

    @property
    def serial(self) -> typing.Optional[str]:
        """The USB device's serial number."""
        return self._serial

    @serial.setter
    def serial(self, serial: typing.Optional[str]) -> None:
        if not isinstance(serial, (str, type(None))):
            raise TypeError("serial")
        self._serial = serial

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        """Converts the object into a dictionary.

        Returns:
            dict: Device object represented as dictionary.
        """
        dct = super().to_dict()
        if self.vendor_id is not None:
            dct["vendor_id"] = self.vendor_id
        if self.product_id is not None:
            dct["product_id"] = self.product_id
        if self.revision_id is not None:
            dct["revision_id"] = self.revision_id
        if self.serial is not None:
            dct["serial"] = self.serial
        return dct

    def from_dict(self, dct: typing.Dict[str, typing.Any], old: bool = False) -> None:
        """Fills the attributes from a dictionary.

        Args:
            d: A dictionary containing values, used to fill these object's attributes
            old: True, if the addresses in `d` should be set as `_old_addresses` because they are
                 not upt-to-date. False (default), if the addresses should be set to these values.
        """
        super().from_dict(dct, old=old)
        self.vendor_id = dct["vendor_id"] if "vendor_id" in dct else None
        self.product_id = dct["product_id"] if "product_id" in dct else None
        self.revision_id = dct["revision_id"] if "revision_id" in dct else None
        self.serial = dct["serial"] if "serial" in dct else None

    def from_device(self, other: "USBDevice") -> None:
        """Updates self from another device.

        Addresses that are currently in `address` or `address_aliases`, will be moved to
        `_old_addresses`.

        Args:
            other: Device that is used to update self.
        """
        if other is self:
            # If the other object is the same as this, There is nothing to do
            return  # pragma: no cover
        super().from_device(other)
        if other.vendor_id is not None:
            self.vendor_id = other.vendor_id
        if other.product_id is not None:
            self.product_id = other.product_id
        if other.revision_id is not None:
            self.revision_id = other.revision_id
        if other.serial is not None:
            self.serial = other.serial

    def __eq__(self, other: "USBDevice") -> bool:
        """Compares this device object with another by comparing their `unique_identifier`s.

        Args:
            other: Other device object to compare with this one.

        Returns:
            bool: True, if the objects are equal, otherwise False.
        """
        if not super().__eq__(other):
            return False

        return self.vendor_id == other.vendor_id and \
               self.product_id == other.product_id and \
               self.revision_id == other.revision_id and \
               self.serial == other.serial


class LANDevice(Device):
    """Special device for ethernet devices."""

    def __init__(self):
        super().__init__()
        self._mac_address = None

    @property
    def device_type(self) -> DeviceType:
        """Corresponding `DeviceType`-object"""
        return DeviceType.LAN

    @property
    def unique_identifier(self) -> typing.Dict[str, typing.Any]:
        """Returns an unique identifier for this device. This makes device objects of the same or
        similar type comparable.

        The unique identifier of an ethernet device is its mac address (physical address).
        """
        return dict(mac_address=self.mac_address)

    @property
    def mac_address(self) -> typing.Optional[str]:
        """The mac address (physical address) of this ethernet device.

        When setting the mac address, it is automatically converted into a standardized format.
        """
        return self._mac_address

    @mac_address.setter
    def mac_address(self, mac_address: typing.Optional[str]) -> None:
        self._mac_address = self.format_mac(mac_address)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        """Converts the object into a dictionary.

        Returns:
            dict: Device object represented as dictionary.
        """
        dct = super().to_dict()
        if self.mac_address is not None:
            dct["mac_address"] = self.mac_address
        return dct

    def from_dict(self, dct: typing.Dict[str, typing.Any], old: bool = False) -> None:
        """Fills the attributes from a dictionary.

        Args:
            d: A dictionary containing values, used to fill these object's attributes
            old: True, if the addresses in `d` should be set as `_old_addresses` because they are
                 not upt-to-date. False (default), if the addresses should be set to these values.
        """
        super().from_dict(dct, old=old)
        self.mac_address = dct["mac_address"] if "mac_address" in dct else None

    def from_device(self, other: "LANDevice") -> None:
        """Updates self from another device.

        Addresses that are currently in `address` or `address_aliases`, will be moved to
        `_old_addresses`.

        Args:
            other: Device that is used to update self.
        """
        if other is self:
            # If the other object is the same as this, There is nothing to do
            return  # pragma: no cover
        super().from_device(other)
        if other.mac_address is not None:
            self.mac_address = other.mac_address

    def __eq__(self, other: "LANDevice") -> bool:
        """Compares this device object with another by comparing their `unique_identifier`s.

        Args:
            other: Other device object to compare with this one.

        Returns:
            bool: True, if the objects are equal, otherwise False.
        """
        if not super().__eq__(other):
            return False

        return self.mac_address == other.mac_address

    @staticmethod
    def format_mac(mac_address: typing.Optional[str]) -> typing.Optional[str]:
        """Checks if the mac address is formatted correctly. If so, the mac address is formatted in
        a standardized way (upper letters and colons as separators).

        Args:
            mac_address: A mac address with colons, hyphens or dots as separators. None is also
                         allowed.

        Returns:
            str: The correctly formatted mac address or None, if `mac_address` was None, too.

        Raises:
            TypeError: If `mac_address` has an invalid format and is not interpretable as a mac
                       address.
        """
        if mac_address is None:
            # None is allowed, but the return value is None, too
            return None
        elif not isinstance(mac_address, str):
            raise TypeError("address")

        if not hasattr(LANDevice, "_regex_mac"):
            # Lazy instantiate the compiled regular expression pattern
            LANDevice._regex_mac = re.compile(r"^([0-9A-Fa-f]{2}[.:\-]){5}([0-9A-Fa-f]{2})$")
        if not LANDevice._regex_mac.match(mac_address):
            # Invalid format of the mac address
            raise TypeError(f"Invalid mac address format: {mac_address}")
        # Return uppercase mac-address with colons as separators
        return mac_address.replace("-", ":").replace(".", ":").upper()


DeviceTypeType = typing.Union[DeviceType, str, typing.Type[Device], Device]


class DeviceTypeDict(dict):
    """A dictionary that accepts `DeviceType`'s or strings as keys. The keys are automatically
    converted, so it makes no difference if a `DeviceType`-object or a string was used.
    """

    def __setitem__(self, key: DeviceTypeType, value: typing.Any) -> None:
        """Sets self[key] to value.

        Args:
            key: The key used to store the value. If the key is a string, it is converted into a
                 `DeviceType`-object.
            value: Value to store at self[key].
        """
        return super().__setitem__(self._get_key(key), value)

    def __getitem__(self, key: DeviceTypeType) -> typing.Any:
        """Gets the value at self[key].

        Args:
            key: The key used to store the value. If the key is a string, it is converted into a
                 `DeviceType`-object.

        Returns:
            The value at self[key].
        """
        return super().__getitem__(self._get_key(key))

    def __delitem__(self, key: DeviceTypeType) -> None:
        """Deletes self[key].

        Args:
            key: The key used to store the value. If the key is a string, it is converted into a
                 `DeviceType`-object.
        """
        return super().__delitem__(self._get_key(key))

    def __contains__(self, key: DeviceTypeType) -> bool:
        """Returns key in self"""
        return super().__contains__(self._get_key(key))

    @staticmethod
    def _get_key(key: DeviceTypeType) -> DeviceType:
        """Converts a string into `DeviceType`, if necessary.

        Args:
            key: A dictionary key of type string or `DeviceType`.

        Returns:
            DeviceType: If key was already a `DeviceType` that key is returned. If it was a string
                        it is converted into a `DeviceType`.
        """
        try:
            return DeviceType(key)
        except (ValueError, TypeError) as exc:
            raise KeyError(key) from exc
