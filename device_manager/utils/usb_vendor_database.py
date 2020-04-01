import re
import urllib.request
from typing import Dict, Optional, Tuple

__all__ = ["USBVendorDatabase"]


class USBVendorDatabase:
    """A static class that maps vendor/product ids to their corresponding names."""

    __vendors = None

    @staticmethod
    def _download_vendors() -> Dict[int, Dict[Optional[int], str]]:
        """Downloads all vendor/product ids and their corresponding names.

        Returns:
            dict: Mapping of all known vendor/product ids with their corresponding names.
        """
        response = urllib.request.urlopen("http://www.linux-usb.org/usb.ids")
        response_str = response.read().decode(encoding="latin1")
        lines = response_str.splitlines()
        read = False

        vendors = dict()

        for line in lines:
            line = line.rstrip()
            if line == "# Vendors, devices and interfaces. Please keep sorted.":
                read = True
                continue
            elif line == "# List of known device classes, subclasses and protocols":
                read = False
                break

            if read:
                if re.match("^[0-9a-f]{4}", line):
                    # Vendor line
                    last_vendor = int(line[:4], base=16)
                    if last_vendor not in vendors:
                        vendors[last_vendor] = dict()
                    vendors[last_vendor][None] = re.sub("\"", "\\\"", re.sub("\?+", "?", repr(
                        line[4:].strip())[1:-1].replace("\\", "\\\\")))
                elif re.match("^\t[0-9a-f]{4}", line):
                    # Product line
                    line = line.strip()
                    product = int(line[:4], base=16)
                    vendors[last_vendor][product] = re.sub("\"", "\\\"", re.sub("\?+", "?", repr(
                        line[4:].strip())[1:-1].replace("\\", "\\\\")))

        return vendors

    @classmethod
    def get_vendor_product_name(cls, vendor_id: int, product_id: int) \
            -> Tuple[Optional[str], Optional[str]]:
        """Returns names for a specific combination of vendor and product id.

        Args:
            vendor_id: Manufacturer id, defined by the USB committee.
            product_id: Model code, defined by the model's manufacturer.

        Returns:
            A tuple of two names. The first one for the vendor, the second one for the product.
        """
        if not cls.__vendors:
            cls.__vendors = cls._download_vendors()

        vendor = None
        product = None

        try:
            vendor = cls.__vendors[vendor_id][None]
            product = cls.__vendors[vendor_id][product_id]
        except KeyError:
            pass

        return vendor, product

    @classmethod
    def __new__(cls, *args, **kwargs) -> None:
        # Do nothing, because this class is static
        return None
