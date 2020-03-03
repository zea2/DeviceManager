#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Base classes for device scanners.

Authors:
    Lukas Lankes, Forschungszentrum Jülich GmbH - ZEA-2, l.lankes@fz-juelich.de
"""

import abc
import re
import typing
import warnings

from ..device import Device, LANDevice

try:
    from .nmap import NMAPWrapper
    _NMAP_IMPORTED = True
except (ImportError, ModuleNotFoundError):
    _NMAP_IMPORTED = False
    warnings.warn("python-nmap is not installed. Without this package you may not find all "
                  "ethernet devices in your local network. When installing python-nmap, do not "
                  "forget to install the nmap executable as well, if it is not installed, yet. And "
                  "make sure it is also included in the PATH environmental variable.")

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
        self._scan(rescan)
        return tuple(self._devices)

    def find_devices(self, rescan: bool = False, **filters) -> typing.Sequence[Device]:
        """Lists all connected devices that match the filter.

        Args:
            rescan: True, if the protocol should be scanned again. False, if you only want to
                    scan, if there are no results from a previous scan.
            **filters: User-defined filters. Only devices that match these filters will be returned.

        Returns:
            tuple: A sequence of all connected devices that match the filter.
        """
        self._scan(rescan)
        return tuple(device for device in self._devices if self._match_filters(device, **filters))

    @abc.abstractmethod
    def _scan(self, rescan: bool) -> None:
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
        nmap_search_path: One or multiple paths where to search for the nmap executable.
                          Or None (default) to use default search paths.
    """

    def __init__(self,
                 nmap_search_path: typing.Optional[typing.Union[str, typing.Iterable[str]]] = None):
        super().__init__()
        self._nmap = None
        # Regular Expression: "  <ip address>  <hardware type>  <mac address>  ..."
        self._arp_regex = re.compile(r"^[ \t]*((?:\d{1,3}\.){3}\d{1,3})[ \t]+\w*[ \t]+"
                                     r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})")

        if _NMAP_IMPORTED:
            try:
                self._nmap = NMAPWrapper(notify_parent_done=lambda b: self._scan(True),
                                         nmap_search_path=nmap_search_path)
            except FileNotFoundError as exc:
                # nmap could not be found on the search path(s)
                warnings.warn(str(exc))

    @property
    def nmap(self) -> typing.Optional["NMAPWrapper"]:
        """Wrapper for a nmap port scanner.

        May be None, if nmap could not be imported."""
        return self._nmap

    def find_devices(self, rescan: bool = False, **filters) -> typing.Sequence[Device]:
        """Lists all connected ethernet devices that match the filter.

        Args:
            rescan: True, if the protocol should be scanned again. False, if you only want to scan,
                    if there are no results from a previous scan.
            **filters: User-defined filters. Only devices that match these filters will be returned.

        Returns:
            tuple: A sequence of all connected devices that match the filter."""
        if "mac_address" in filters:
            filters["mac_address"] = LANDevice.format_mac(filters["mac_address"])
        return super().find_devices(rescan=rescan, **filters)

    def _scan(self, rescan: bool) -> None:
        """Scans the arp cache for ip and mac addresses.

        Args:
            rescan: True, to scan again. False, if you only want to scan, if there are no
                    results from a previous scan.
        """
        if len(self._devices) > 0 and not rescan:
            return
        devices = self._get_arp_cache()
        if self.nmap is not None:
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

    @abc.abstractmethod
    def _get_arp_cache(self) -> typing.Dict[str, LANDevice]:
        """Runs the arp command and extracts ip and mac addresses from the command's output.

        A subclass must override this function because this function is platform dependent.

        Returns:
            dict: A dictionary, mapping strings to `LANDevice`s. The dictionary contains all results
                  of the arp command, that contain a valid ip and mac address.
        """
        raise NotImplementedError()
