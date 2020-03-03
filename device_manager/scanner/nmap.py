#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The nmap wrapper is used to easily and efficiently perform nmap scans with python-nmap.

It wraps the relevant scan functions of nmap's `PortScanner`. The scan results are stored locally to
make them accessable later if needed. And this class also provides a way to scan asynchronously for
network devices at a specific address or subnet.

Authors:
    Lukas Lankes, Forschungszentrum Jülich GmbH - ZEA-2, l.lankes@fz-juelich.de
"""

import os
import threading
import typing
import warnings

try:
    import nmap
    _NMAP_IMPORTED = True
except (ImportError, ModuleNotFoundError):
    _NMAP_IMPORTED = False
    warnings.warn("python-nmap is not installed. Without this package you may not find all "
                  "ethernet devices in your local network. When installing python-nmap, do not "
                  "forget to install the nmap executable as well, if it is not installed, yet. And "
                  "make sure it is also included in the PATH environmental variable.")

from ..device import LANDevice

__all__ = ["NMAPWrapper"]

####################################################################################################


class NMAPWrapper:
    """Wrapper class for `nmap.PortScanner`. It class manages network scans via nmap and converts
    the results in `Device`s.

    Args:
        notify_parent_done: An optional function object which is called after this scan is
                            performed. The function needs to accept one argument of type bool. This
                            argument will be True, if the scan succeeded and False, if not.
        nmap_search_path: One or multiple paths where to search for the nmap executable.
                          Or None (default) to use default search paths.
    """

    def __init__(self, notify_parent_done: typing.Optional[typing.Callable[[bool], None]] = None,
                 nmap_search_path: typing.Optional[typing.Union[str, typing.Iterable[str]]] = None):
        super().__init__()

        nmap_kwargs = {}
        if nmap_search_path is not None:
            # If an executable path is passed, use it as argument for nmap.PortScanner
            if isinstance(nmap_search_path, str):
                nmap_search_path = (nmap_search_path,)  # It needs to be an iterable
            nmap_kwargs["nmap_search_path"] = nmap_search_path

        self._nmap = None

        if _NMAP_IMPORTED:
            try:
                self._nmap = nmap.PortScanner(**nmap_kwargs)
            except nmap.PortScannerError:
                # An error is raised, if the nmap-executable was not found
                warnings.warn("Could not create a nmap.PortScanner instance. Maybe nmap is not "
                              "installed on your machine or it is not specified in PATH. If nmap "
                              "is already installed try specifying its path with the "
                              "'nmap_search_path'-parameter.")

        self._nmap_results = []
        self._nmap_thread = None
        self._notify_parent_done = notify_parent_done

    @property
    def raw_devices(self) -> typing.Sequence[typing.Dict]:
        """The raw search results as they are returned by a scan with nmap. The results of all
        previous scans are included.
        """
        return tuple(self._nmap_results)

    @property
    def devices(self) -> typing.Sequence[LANDevice]:
        """The results of all previous scans with namp. The raw results are converted into `Device`-
        objects.
        """
        raw_devices = self.raw_devices
        devices = {}
        for raw_device in raw_devices:
            try:
                # Extract ip addresses and mac address
                addresses = raw_device["addresses"]
                mac_address = addresses["mac"]
            except KeyError:
                continue

            ip_addresses = []
            # Append all IPv4 and IPv6 addresses
            for key in ["ipv4", "ipv6"]:
                try:
                    ip_addresses.append(addresses[key])
                except KeyError:
                    continue

            # If there is already a device for this mac address, just update the device's addresses
            if mac_address in devices:
                address_aliases = [ip_address for ip_address in ip_addresses
                                   if ip_address not in devices[mac_address].all_addresses]
                # Append unknown addresses to aliases
                if len(address_aliases) > 0:
                    devices[mac_address].address_aliases = [*devices[mac_address].address_aliases,
                                                            address_aliases]
            else:
                dev = LANDevice()
                dev.mac_address = mac_address
                dev.address = ip_addresses[0]
                if len(ip_addresses) > 1:
                    # If multiple addresses were found, add the others as aliases
                    dev.address_aliases = ip_addresses[1:]
                devices[mac_address] = dev
        return tuple(devices.values())

    def clear_devices(self) -> None:
        """Deletes all previous scan results."""
        self._nmap_results.clear()

    def scan(self, hosts: typing.Union[str, typing.Iterable[str]]) -> bool:
        """Performs a network scan with nmap (synchronously).

        Args:
            hosts: One host as string or multiple hosts as iterable of strings. Multiple hosts can
                   also be written as single string with a space as separator. A host can use one of
                   the following formats to scan a single host:
                   - ip address (e.g. 192.168.1.10)
                   - hostname (e.g. localhost)
                   - domain (e.g. mydevice.company.com)
                   Or to scan a whole subnet of a local network:
                   - ip subnet (e.g. 192.168.1.0/24 for a 24bit netmask)
        """
        return self._scan(hosts, None)

    def scan_async(self, hosts: typing.Union[str, typing.Iterable[str]],
                   on_done: typing.Optional[typing.Callable[[bool], None]] = None) -> bool:
        """Performs a network scan with nmap asynchronously.

        Args:
            hosts: One host as string or multiple hosts as iterable of strings. Multiple hosts can
                   also be written as single string with a space as separator. A host can use one of
                   the following formats to scan a single host:
                   - ip address (e.g. 192.168.1.10)
                   - hostname (e.g. localhost)
                   - domain (e.g. mydevice.company.com)
                   Or to scan a whole subnet of a local network:
                   - ip subnet (e.g. 192.168.1.0/24 for a 24bit netmask)
            on_done: An optional function object which is called after this scan is performed. The
                     function needs to accept one argument of type bool. This argument will be True,
                     if the scan succeeded and False, if not.

        Returns:
            bool: True, if the asynchronous scan was started. False, if a scan is already running.
        """
        if self.is_scan_alive():
            return False
        self._nmap_thread = threading.Thread(target=self._scan, args=(hosts, on_done))
        self._nmap_thread.start()
        return True

    def is_scan_alive(self) -> bool:
        """Checks if an asynchronous scan is still running.

        Returns:
            bool: True, if an asynchronous scan is running. Otherwise, false.
        """
        if self._nmap_thread is None:
            return False
        elif self._nmap_thread.is_alive():
            return True
        else:
            # If the thread is not alive, but not None, set it to None, because it is not needed
            # anymore.
            self._nmap_thread = None
            return False

    def wait_for_scan(self, timeout: typing.Optional[float] = None) -> bool:
        """If an asynchronous scan is running, this function waits until the scan is finished.

        Args:
            timeout: A floating point number specifying a timeout (maximum time to wait) in seconds.
                     If timeout is None, this function will block until the scan is completed.

        Returns:
            bool: True, if the scan is completed or not running at all. False, if the timeout
                  happened.
        """
        # If no scan thread is alive, there is nothing to wait for
        if not self.is_scan_alive():
            return True
        self._nmap_thread.join(timeout=timeout)
        return self.is_scan_alive()

    def _scan(self, hosts: typing.Union[str, typing.Iterable[str]],
              on_done: typing.Optional[typing.Callable[[bool], None]]) -> bool:
        """Performs a network scan with nmap (synchronously).

        Args:
            hosts: One host as string or multiple hosts as iterable of strings. Multiple hosts can
                   also be written as single string with a space as separator. A host can use one of
                   the following formats to scan a single host:
                   - ip address (e.g. 192.168.1.10)
                   - hostname (e.g. localhost)
                   - domain (e.g. mydevice.company.com)
                   Or to scan a whole subnet of a local network:
                   - ip subnet (e.g. 192.168.1.0/24 for a 24bit netmask)
            on_done: An optional function object which is called after this scan is performed. The
                     function needs to accept one argument of type bool. This argument will be True,
                     if the scan succeeded and False, if not.
        """
        if self._nmap is None:
            # The nmap-PortScanner could not be instantiated. So, either nmap or python-nmap are not
            # installed.
            warnings.warn("Could not perform a network scan with nmap. Either \"nmap\" is not "
                          "installed on your system or \"python-nmap\" is missing in your python "
                          "environment. To use the nmap features, make sure both are installed.")
            return False

        if not isinstance(hosts, str):
            # nmap expects a single string as host-argument, multiple hosts are separated by spaces
            hosts = " ".join(hosts)
        try:
            exception = None
            for arguments in ["-sA -F --min-parallelism 1024 --privileged",
                              "-sT -F --min-parallelism 1024"]:
                try:
                    # Try to perform a TCP-ACK scan, which seems to be the fastest one, but it
                    # requires admin privileges on linux. If the user has the requires privileges it
                    # should work.
                    self._nmap.scan(hosts, arguments=arguments)
                    scan_info = self._nmap.scaninfo()
                    if "error" in scan_info:
                        # The scan terminated correctly, but an stderr contained some outputs
                        raise nmap.PortScannerError(os.linesep.join(scan_info["error"]))
                    break  # Success
                except nmap.PortScannerError as exc:
                    # If an error occurs, this could be due to missing admin privileges. So the next
                    # element from the arguments is tried which needs less privileges.
                    exception = exc
            else:
                if exception is not None:
                    raise exception

            # Append all new scan results
            for host in self._nmap.all_hosts():
                device = self._nmap[host]
                # If the same device is already known, there is no need to add it again
                if device not in self._nmap_results:
                    self._nmap_results.append(device)
            result = True
        except (UnicodeDecodeError, nmap.PortScannerError):
            # Some error messages containing special characters cannot be decoded on windows. That
            # is why the UnicodeDecodeError is caught here
            result = False
        finally:
            # Call the functions, because the scan is finished
            if self._notify_parent_done is not None:
                # If a callable was provided in the constructor, call it now
                self._notify_parent_done(result)
            if on_done is not None:
                # Additionally, a callable can be passed in this function. If such a function was
                # passed, call it now
                on_done(result)

        return result
