#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The device manager can store devices and makes them accessible by the user.

The `DeviceManager`-class works like a dictionary that stores `Device`-objects by user-defined names
as dictionary-keys. But the device manager is slightly more intelligent than a ordinary dictionary.
It automatically searches for device addresses, if these are not known, yet. For this purpose, it
contains device scanners for each supported device type. These scanners can also be used by the user
of the device manager. To add a device to the device manager, it is not required to create an device
object with all the information. It is sufficient to set the device's address as string (and
optionally the device type, to only search with a specific scanner).
Additionally, the device manager can be serialized into a JSON-file and it can also be loaded from
this file. To make the file access easier, the function load_device_manager can be used.

Examples:
    Creating a DeviceManager-object:

    >>> dm = DeviceManager()

    Finding a device by its identifier:

    >>> usb_device = dm.scanner["usb"].find_devices(serial="1234567890AB")

    Adding a new device and accessing it

    >>> dm["my-device"] = usb_device
    >>> assert dm["my-device"] is usb_device

    Adding a device by its address, is also possible

    >>> dm["my-device"] = "192.168.1.23"  # Searches all supported device types
    >>> dm["my-device", "lan"] = "192.168.1.23"  # Only searches ethernet (lan) devices

    Last, but not least, you can serialize the DeviceManager into a JSON file:

    >>> with open("filename.json", "w") as f:
    >>>     dm.save(f)  # Save the device manager to "filename.json"
    >>> with load_device_manager("filename.json") as dev_man:
    >>>     device = dev_man["my-device", "usb"]  # returns `usb_device`
"""

import contextlib
import copy
import json
import typing
import warnings

from .device import Device, DeviceType, DeviceTypeDict, DeviceTypeType
from .scanner import DeviceScanner

__all__ = ["DeviceManager", "load_device_manager"]

####################################################################################################


@contextlib.contextmanager
def load_device_manager(filename: str, autosave: bool = False) \
        -> typing.ContextManager["DeviceManager"]:
    """Loads a device manager from a json formatted file.

    Args:
        filename: Path to json file which contains the serialized device manager
        autosave: True to save the device manager at the end of the with-statement, but only if no
                  error occurred. If you want your device manager to be saved, use a try-except
                  block inside the with-block.

    Returns:
        A context manager which can be used in a with-statement. That context manager returns a
        DeviceManager if it is used in a with-statement.
    """
    manager = DeviceManager()
    # Load the device manager from `filename`
    with open(filename, "r") as file:
        manager.load(file)
    # Return the device manager that was loaded from `filename`
    yield manager
    if autosave:
        # If autosave is True, the device manager is saved in the end of the with-block
        with open(filename, "w") as file:
            manager.save(file)


class DeviceDict:
    """A device dictionary containing devices that can be saved by a user-defined name. Multiple
    devices can be saved with the same name, as long as the device type is different.

    This is how the dictionary is used:
    - Storing a device: self[name] = `Device`-object or self[name] = device-address as string.
    - Getting/deleting a device with self[name] returns a `DeviceTypeDict` containing all available
      device types of this device.
    - Getting/deleting a device with self[name, type] returns a device of a specific `DeviceType`.
      It is the same as self[name][type], so type is the key of the underlying `DeviceTypeDict`
    """

    def __init__(self):
        self._dict = {}

    def __len__(self) -> int:
        """Returns len(self)"""
        return len(self._dict)

    def __setitem__(self, key: str, value: Device) -> None:
        """Sets self[key] to value. The value is a `Device`-object.

        Args:
            key: The key (device name) used to store the value (device).
            value: Value to store at self[key]. Because the value needs to be a `Device`-object, its
                   device type (key for the underlying `DeviceTypeDict`) is determined
                   automatically.
        """
        self.set(key, value)

    def __getitem__(self, key: typing.Union[str, typing.Tuple[str, DeviceTypeType]]) \
            -> typing.Union[typing.Dict[DeviceType, Device], Device]:
        """Gets the value(s) behind self[key] (or self[key, type], if key is a tuple).

        Args:
            key: The key whose value is requested. It can be a single string which specifies the
                 device's name. Or the key is a tuple. If this is the case, the first component
                 specifies the device's name, as well. The second component specifies a `DeviceType`
                 that is used as key for the `DeviceTypeDict`: So, self[name, type] is equal to
                 self[name][type].

        Returns:
            If key is a single string, the return value is a `DeviceTypeDict`-object containing all
            available device types for this device. If key is a tuple, the second component
            specifies the requested device type to return, so if key is (name, type), the return
            value is the same as self[name][type].
        """
        return self.get(key)

    def __delitem__(self, key: typing.Union[str, typing.Tuple[str, DeviceTypeType]]) -> None:
        """Deletes the value(s) behind self[key].

        Args:
            key: The key to delete. The key can be a single string or a tuple. If a tuple is used,
                 the first component is the same key as if a single string is used.
                 The second component describes a specific device type to delete.
        """
        self.remove(key)

    def __iter__(self):
        """Returns iter(self)"""
        yield from self.keys()

    def __contains__(self, key: str) -> bool:
        """Returns True, if self contains key. Otherwise, False."""
        return key in self._dict

    def set(self, key: str, value: Device) -> None:
        """Sets self[key] to value. The value is a `Device`-object.

        Args:
            key: The key (device name) used to store the value (device).
            value: Value to store at self[key]. Because the value needs to be a `Device`-object, its
                   device type (key for the underlying `DeviceTypeDict`) is determined
                   automatically.
        """
        if not isinstance(key, str):
            raise TypeError("name")  # pragma: no cover
        if isinstance(value, Device):
            # Extract device type from device
            device_type = value.device_type
        else:
            raise TypeError("device")  # pragma: no cover
        if key not in self._dict:
            # If the key (name) is unknown, create a new dictionary
            self._dict[key] = DeviceTypeDict()
        self._dict[key][device_type] = value

    def get(self, key: typing.Union[str, typing.Tuple[str, DeviceTypeType]]) \
            -> typing.Union[DeviceTypeDict, Device]:
        """Gets the value(s) behind self[key] (or self[key, type], if key is a tuple).

        Args:
            key: The key whose value is requested. It can be a single string which specifies the
                 device's name. Or the key is a tuple. If this is the case, the first component
                 specifies the device's name, as well. The second component specifies a `DeviceType`
                 that is used as key for the `DeviceTypeDict`: So, self[name, type] is equal to
                 self[name][type].

        Returns:
            If key is a single string, the return value is a `DeviceTypeDict`-object containing all
            available device types for this device. If key is a tuple, the second component
            specifies the requested device type to return, so if key is (name, type), the return
            value is the same as self[name][type].
        """
        name, device_type = self._getitem_key(key)
        try:
            if device_type is None:
                # Return copy of dictionary, to prevent users from adding/removing devices from the
                # internal dictionary. But the devices should be references to the real devices.
                devices = self._dict[name]
                if len(devices) == 1:
                    return next(iter(devices.values()))
                else:
                    return copy.copy(devices)
            else:
                # Return the device of the specified type
                return self._dict[name][device_type]
        except KeyError:
            raise KeyError(key)

    def remove(self, key: typing.Union[str, typing.Tuple[str, DeviceTypeType]]) -> None:
        """Deletes the value(s) behind self[key].

        Args:
            key: The key whose value is requested. It can be a single string which specifies the
                 device's name. Or the key is a tuple. If this is the case, the first component
                 specifies the device's name, as well. The second component specifies a `DeviceType`
                 that is used as key for the `DeviceTypeDict`: So, self[name, type] is equal to
                 self[name][type].
        """
        name, device_type = self._getitem_key(key)
        try:
            if device_type is None:
                # Delete all devices for the name
                del self._dict[name]
            else:
                # Only delete the specified device type for the name
                del self._dict[name][device_type]
                if len(self._dict[name]) <= 0:
                    # If there were no other device types, the name can be deleted, too
                    del self._dict[name]
        except KeyError:
            raise KeyError(key)

    def clear(self) -> None:
        """Removes all items from self"""
        self._dict.clear()

    def keys(self) -> typing.Sequence[str]:
        """Returns all dictionary keys (= device names)"""
        return tuple(self._dict.keys())

    def values(self) -> typing.Sequence[DeviceTypeDict]:
        """Returns all devices as `DeviceTypeDict`s"""
        return tuple(self._dict.values())

    def items(self) -> typing.Sequence[typing.Tuple[str, DeviceTypeDict]]:
        """Returns the key-value-mapping as tuples"""
        return tuple(self._dict.items())

    @staticmethod
    def _getitem_key(key: typing.Union[str, typing.Tuple[str, DeviceTypeType]]) \
            -> typing.Tuple[str, typing.Optional[DeviceType]]:
        """Checks if the key is valid and converts it into a key-tuple.

        Args:
            key: The dictionary key can be a single string which specifies the device's name. Or the
                 key is a tuple. If this is the case, the first component specifies the device's
                 name, as well. The second component specifies a `DeviceType` that is used as key
                 for the `DeviceTypeDict`: So, self[name, type] is equal to self[name][type].

        Returns:
            The key, converted into a tuple
        """
        if isinstance(key, str):
            # If the key is a string, the second tuple-component is None
            name = key
            device_type = None
        elif isinstance(key, tuple):
            # If the key is a tuple, check its length
            if len(key) != 2:
                raise TypeError("DeviceManager keys must be strings or tuples of length 2, not a "
                                "tuple of length {}".format(len(key)))
            # Extract the key components
            name, device_type = key
        else:
            # Other types are not allowed
            raise TypeError("DeviceManager keys must be strings or tuples, not {}".format(
                type(key)))
        return name, device_type  # key as tuple


class DeviceManager(DeviceDict):
    """The `DeviceManager` stores devices by user-defined names. Also multiple devices can be stored
    for the same name as long as the device types are different.

    Usage:
    - self[name] returns a `DeviceTypeDict` containing the devices of all available device types.
    - self[name, type] or self[name][type] can also be used to request a specific type of device.

    Args:
        file: A handle to a json formatted file, to load the device manager data from.
    """
    def __init__(self, **kwargs):
        super().__init__()
        self._scanner = DeviceScanner(**kwargs)
        self._scanner.list_devices()

    @property
    def scanner(self) -> DeviceScanner:
        """A `DeviceScanner` object that is used to search for devices"""
        return self._scanner

    def find_by_address(self, address: str, device_type: typing.Optional[DeviceTypeType] = None) \
            -> typing.Optional[Device]:
        """Finds a device by its address.

        Args:
            address: The device's address or port.
            device_type: The device type or None, to search for all device types.

        Returns:
            Device: The device at the given address or None if no device was found.
        """
        # Check the device cache if the address is already known
        devices = self._scanner[device_type].find_devices(address=address)
        if len(devices) <= 0:
            # If no device was found, use the argument rescan to rescan for the address
            devices = self._scanner[device_type].find_devices(address=address, rescan=True)
        if len(devices) <= 0:
            # If still no device was found and the specified device type was LAN (or None, to search
            # all types), nmap is used to scan for the address. This might get more accurate results
            # pylint: disable=no-member
            if device_type in [DeviceType.LAN, None] and \
                    self._scanner[DeviceType.LAN].nmap is not None:  # pragma: no cover
                try:
                    self._scanner[DeviceType.LAN].nmap.scan(address)
                except Exception:
                    pass
                # Read out the device cache again, to also get the nmap results
                devices = self._scanner[DeviceType.LAN].find_devices(address=address)
        if len(devices) > 0:
            if len(devices) > 1:  # pragma: no cover
                # This should not happen, but who knows
                warnings.warn("Expected only one device for address \"{}\", not {}".format(
                    address, len(devices)))
            # Return the first device that was found (hopefully, this was the only one)
            return devices[0]
        else:
            return None

    def find_by_device(self, search_device: Device, scan: bool = False) -> typing.Optional[Device]:
        """Finds a device that matches the unique identifiers of a given device.

        Args:
            search_device: device whose identifiers are used to search for an up-to-date device.
            scan: True, to scan for devices. False, to scan only, if there are currently no
                  addresses for the device. If the device is already known and connected, it is
                  taken from the cache.

        Returns:
            A device that matches the identifiers of `search_device`. If `search_device` already has
            addresses stored and `scan` is False, the `search_device` is returned. Otherwise, this
            function will search for a device that matches the identifiers of `search_device`. The
            found device will be returned with addresses that are up-to-date. If this search does
            not lead to any results, None is returned.
        """
        if not isinstance(search_device, Device):
            raise TypeError("Invalid device type: {}".format(type(search_device)))
        if len(search_device.all_addresses) > 0 and not scan:
            # If the caller does not want to rescan and there are already addresses known for this
            # device.
            return search_device
        scanner = self.scanner[search_device.device_type]
        # Rescan for the device
        devices = scanner.find_devices(rescan=True, **search_device.unique_identifier)
        if len(devices) <= 0:
            # If still no device was found and the type of the specified device type was LAN, nmap
            # is used to scan for the address. This might get more accurate results
            if search_device.device_type == DeviceType.LAN \
                    and scanner.nmap.valid:  # pragma: no cover
                addresses = [*search_device.all_addresses, *search_device._old_addresses]
                try:
                    scanner.nmap.scan(addresses)
                except Exception:
                    pass
                # Read out the device cache again, to also get the nmap results. No rescan required.
                devices = scanner.find_devices(**search_device.unique_identifier)
        if len(devices) > 0:
            if len(devices) > 1:  # pragma: no cover
                # This should not happen, but who knows
                warnings.warn("Expected only one device as search result, not {}".format(
                    len(devices)))
            result = copy.copy(search_device)
            result.from_device(devices[0])
            # Return the first device that was found (hopefully, this was the only one)
            return result
        else:
            return None

    def set(self, key: typing.Union[str, typing.Tuple[str, DeviceTypeType]],
            value: typing.Union[Device, str], scan: bool = False) -> None:
        """Sets self[key] to value. The value is a `Device`-object or a string.

        Args:
            key: The key (device name) used to store the value (device). If `value` is an address of
                 type string, you can also provide a second key to specify the device type. This
                 will speed up the search for the device's address because only the corresponding
                 protocol is used to search for the address.
            value: Value to store at self[key]. The value can be a `Device`-object or a string. If
                   a string is used, it is interpreted as the device's address. The device at this
                   address is determined automatically.
            scan: True, to rescan for the device. If no addresses are known for the device to set, a
                  scan is performed nevertheless. False, if you only want to scan in that case.
        """
        name, device_type = self._getitem_key(key)
        if isinstance(value, str):
            # If value is a string, it is interpreted as the device's address. So the device manager
            # needs to search for the address.
            device = self.find_by_address(value, device_type)
            if device is None:
                raise ValueError("No {}device was found for address \"{}\".".format(
                    (device_type.value + "-") if device_type is not None else "", value))
        elif isinstance(value, Device):
            if device_type is not None and device_type != value.device_type:
                # The device's type does not match the device_type-argument
                raise ValueError("The second component of the specified key ({}) does not match the"
                                 "value's type ({})".format(device_type, value.device_type))
            device = value
            found = self.find_by_device(device, scan=scan)
            if found is not None:
                device.from_device(found)
            elif len(device.all_addresses) > 0:
                # If there are any addresses stored in `device` reset them because they are not
                # up-to-date anymore.
                device.reset_addresses()
        else:
            raise TypeError("value")
        super().set(name, device)

    def get(self, key: typing.Union[str, typing.Tuple[str, DeviceTypeType]], scan: bool = False) \
            -> typing.Union[typing.Dict[DeviceType, Device], Device]:
        """Gets the value(s) behind self[key] (or self[key, type], if key is a tuple). If a device
        is found for the key, this function searches for updated addresses of this device, as soon
        as this was not done in this session before.

        Args:
            key: The key whose value is requested. It can be a single string which specifies the
                 device's name. Or the key is a tuple. If this is the case, the first component
                 specifies the device's name, as well. The second component specifies a `DeviceType`
                 that is used as key for the `DeviceTypeDict`: So, self[name, type] is equal to
                 self[name][type].
            scan: True, to rescan for the device. If no addresses are known for the requested
                  device, a scan is performed nevertheless. False, if you only want to scan in that
                  case.

        Returns:
            If key is a single string, the return value is a `DeviceTypeDict`-object containing all
            available device types for this device. If key is a tuple, the second component
            specifies the requested device type to return, so if key is (name, type), the return
            value is the same as self[name][type].
        """
        device = super().get(key)
        if isinstance(device, Device):
            found = self.find_by_device(device, scan=scan)
            if found is not None:
                device.from_device(found)
            elif len(device.all_addresses) > 0:
                # If there are any addresses stored in `device` reset them because they are not
                # up-to-date anymore.
                device.reset_addresses()
        elif isinstance(device, dict):
            # Search for updated addresses of the stored device, but only if there are no addresses
            # known, yet
            for dev in device.values():
                found = self.find_by_device(dev, scan=scan)
                if found is not None:
                    dev.from_device(found)
                elif len(dev.all_addresses) > 0:
                    # If there are any addresses stored in `device` reset them because they are not
                    # up-to-date anymore.
                    dev.reset_addresses()
        else:  # pragma: no cover
            raise TypeError("Expected Device or dict, got {} instead".format(type(device)))
        return device

    def reset_addresses(self) -> None:
        """Resets the addresses of all stored devices.

        This forces the scanners to rescan for devices, when these are requested again."""
        for devices in self.values():
            for device in devices.values():
                device.reset_addresses()

    def load(self, file: typing.IO, clear: bool = True) -> None:
        """Loads the device managers data from a json formatted file.

        Args:
            file: A handle to a json formatted file, to load the device manager data from.
            clear: True, if all previous data of this device manager should be cleared before
                   loading the file. False, to keep the previous data. In this case, devices with
                   equal keys may be replaced by the file's data.
        """
        if clear:
            # Clear device before loading, if the caller wants so
            self.clear()
        # Convert json file to dictionary
        dct = json.load(file)
        # Add values of the dictionary to self
        for name, raw_devices in dct.items():
            for device_type_name, raw_device in raw_devices.items():
                # Create device of specific type
                device = DeviceType(device_type_name).type()
                # Fill device's attributes from raw dictionary
                device.from_dict(raw_device, old=True)
                self[name] = device

    def save(self, file: typing.IO, pretty: bool = False) -> None:
        """Serializes the device manager to json and saves it to a file.

        Args:
            file: A handle to a file, to save the data at.
            pretty: True, to indent the json file to make it easier to read. If False (default), the
                    file is formatted without newlines or indentation, to reduce the amount of data.
        """
        dct = {}
        # Create a dictionary of all devices serialized to dictionaries
        for name, devices in self.items():
            dct[name] = {}
            for device_type, device in devices.items():
                # Convert/serialize device into a dictionary of its attributes
                dct[name][device_type.value] = device.to_dict()
        # After the devices were converted into dictionaries, they can be serialized to json format
        json.dump(dct, file, indent=(4 if pretty else None))
