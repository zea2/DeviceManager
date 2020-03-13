#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Base classes for device scanners."""

import abc
import typing

from .nmap import NMAPWrapper
from ..device import Device, LANDevice

__all__ = ["BaseDeviceScanner", "BaseLANDeviceScanner"]

####################################################################################################


class BaseDeviceScanner(abc.ABC):
    """Base class for device scanners. Device scanners are used to scan specific protocols (like usb
    or ip). You can get a list of all connected devices or search with a user-defined filter.
    """

    def __init__(self):
        super().__init__()
        self._devices = []

    def list_devices(self, rescan: bool = False) -> typing.Sequence[Device]:
        """Lists all connected devices.

        Args:
            rescan: True, if the protocol should be scanned again. False, if you only want to
                    scan, if there are no results from a previous scan.

        Returns:
            tuple: A sequence of all connected devices.
        """
        return tuple(self._scan(rescan))

    def find_devices(self, rescan: bool = False, **filters) -> typing.Sequence[Device]:
        """Lists all connected devices that match the filter.

        Args:
            rescan: True, if the protocol should be scanned again. False, if you only want to
                    scan, if there are no results from a previous scan.
            **filters: User-defined filters. Only devices that match these filters will be returned.

        Returns:
            tuple: A sequence of all connected devices that match the filter.
        """
        devices = self._scan(rescan)
        return tuple(device for device in devices if self._match_filters(device, **filters))

    @abc.abstractmethod
    def _scan(self, rescan: bool) -> typing.Sequence[Device]:
        """Scans the specific protocol for devices.

        Subclasses must override this function and fill the `_devices` attribute.

        Args:
            rescan: True, if the protocol should be scanned again. False, if you only want to
                    scan, if there are no results from a previous scan.
        """
        raise NotImplementedError()

    @staticmethod
    def _match_filters(device: Device, **filters) -> bool:
        """Checks if the device matches the user-defined filters.

        Args:
            device: The device object, that is about to be checked against the filters.
            **filters: User-defined filters. Only devices that match these filters will be returned.

        Returns:
            bool: True, if the device matches the filters.
        """
        for attr, mask_value in filters.items():
            if attr == "address":
                # If an address filter is passed, check if it is contained in all_addresses. So, the
                # aliases are checked two
                if mask_value not in device.all_addresses:
                    return False
            else:
                try:
                    if attr == "mac_address":
                        mask_value = LANDevice.format_mac(mask_value)
                    if mask_value != getattr(device, attr):
                        return False
                except AttributeError:
                    # If the device does not contain the filter, it does not match the filter
                    return False
        # If no conflict happened, the device matches the filter
        return True


class BaseLANDeviceScanner(BaseDeviceScanner, abc.ABC):
    """A device scanner that scans the local network for ethernet devices.

    Args:
        **kwargs:
          - nmap_search_path: One or multiple paths where to search for the nmap executable.
    """

    def __init__(self, **kwargs):
        super().__init__()
        self._nmap = NMAPWrapper(notify_parent_done=lambda b: self._scan(True), **kwargs)

    @property
    def nmap(self) -> typing.Optional["NMAPWrapper"]:
        """Wrapper for a nmap port scanner.

        May be None, if nmap could not be imported."""
        return self._nmap

    def _scan(self, rescan: bool) -> typing.Sequence[LANDevice]:
        """Scans the arp cache for ip and mac addresses.

        Args:
            rescan: True, to scan again. False, if you only want to scan, if there are no
                    results from a previous scan.
        """
        if len(self._devices) > 0 and not rescan:
            return self._devices

        devices = self._get_arp_cache()
        if self.nmap.valid:  # pragma: no cover
            for dev in self.nmap.devices:
                if dev.mac_address in devices:
                    address_aliases = [ip_address for ip_address in dev.all_addresses
                                       if ip_address not in devices[dev.mac_address].all_addresses]
                    if len(address_aliases) > 0:
                        devices[dev.mac_address].address_aliases = \
                            [*devices[dev.mac_address].address_aliases, address_aliases]
                else:
                    devices[dev.mac_address] = dev
        self._devices = list(devices.values())
        return tuple(self._devices)

    @abc.abstractmethod
    def _get_arp_cache(self) -> typing.Dict[str, LANDevice]:
        """Runs the arp command and extracts ip and mac addresses from the command's output.

        A subclass must override this function because this function is platform dependent.

        Returns:
            dict: A dictionary, mapping strings to `LANDevice`s. The dictionary contains all results
                  of the arp command, that contain a valid ip and mac address.
        """
        raise NotImplementedError()
