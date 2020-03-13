.. _concepts:

Concepts
========

Overview
--------

The DeviceManager-package in general consists of three modules: ``device``, ``scanner`` and
``manager``. Each of these modules is for specific class which are representing the concepts of this
project. The ``device``-module contains the ``Device``-classes which are basic data classes. The
``scanner``-module is a bit more complex, because it wraps different ``DeviceScanner``s for each
type of device and for each supported platform. The ``manager``-module contains the
``DeviceManager`` which manages a dictionary of ``Device``s and uses the ``DeviceScanner`` to
automatically search for devices.

Devices and device scanners are available for each supported device type. Currently supported are:

- USB devices and
- Ethernet/LAN devices.

Additionally, the device scanners use different implementations depending on the host's platform.
These are the supported platforms at this time:

- | Windows
  | *(tested on Windows 10)*

- | Linux
  | *(tested on Ubuntu 18.04)*

Even if the software only was tested on a single distributen/version per platform, it should also
work on most other distributions/versions of Windows and Linux.


Devices
-------

The devices are represented by the abstract class ``Device``. The ``Device``-classes are data
classes storing relevant device information. Every device has the following properties:

- | ``device_type``
  | An abstract property specifying the device's type. The return value is constant within a class

- | ``address``
  | The devices main address or port

- | ``address_aliases``
  | A list of other addresses that can be used to access the device

- | ``all_addresses``
  | A readonly property returning a combined list of ``address`` and ``address_aliases``

- | ``unique_identifier``
  | Another abstract property containing some properties of the device that can be used to uniquely
    identify it. Which properties these are, depends on the device type.

To make each device serializable, it has the functions ``to_dict`` and ``from_dict`` which are used
to convert a ``Device``-object into a standard Python dictionary and vice versa. That can be used to
serialize a ``Device``-object into a JSON- or XML-file, for example. There are many serializer
packages existing for python that can easily convert dictionaries in any common file format.
Additionally, the ``to_dict``-function is very useful to get a look into the ``Device``-object by
printing it to stdout.

The ``device_type`` is represented by the enumeration-class ``DeviceType``. This class contains all
currently supported device types. For each enumeration member there is a corresponding subclass of
``Device``. Currently these types are supported:

- USB devices

  - ``DeviceType.USB``
  - represented by ``USBDevice``

- Ethernet/LAN devices

  - ``DeviceType.LAN``
  - represented by ``LANDevice``


USB devices
^^^^^^^^^^^

USB devices are represented by the class ``USBDevice``. Beside the inherited properties from
``Device`` it has the following ones:

- | ``vendor_id``
  | The manufacturer code provided by the USB committee

- | ``product_id``
  | The model code provided by the device's manufacturer

- | ``revision_id``
  | The revision code

- | ``serial``
  | The device's serial number

As ``unique_identifier`` the ``USBDevice`` returns its ``vendor_id``, ``product_id`` and
``serial``.


Ethernet/LAN devices
^^^^^^^^^^^^^^^^^^^^

Ethernet devices are represented by the ``LANDevice``-class. It has one additional member:

- | ``mac_address``
  | The device's physical address.
  | Setting this property automatically formats the passed MAC-address-string into an internally
    standardized format which makes the comparision of ``LANDevice``-objects much easier.

The ``LANDevice`` uses its ``mac_address`` as ``unique_identifier``.


Device scanners
---------------

Device scanners are used to scan specific ports or protocols for connected devices. Analogously to
the ``Device``-classes and ``DeviceType``-members, there are different device scanners for each
supported device type:

- ``USBDeviceScanner``
- ``LANDeviceScanner``

As their names suggest, the ``USBDeviceScanner`` scans for USB devices and the ``LANDeviceScanner``
for LAN devices. Both are inherited from the ``BaseDeviceScanner`` and both are used exactly the
same way. They consist of just to functions:

- | ``list_devices()``
  | Lists all available devices of the corresponding type.
  | The results are cached internally. On the next call, the device scanner falls back on these
    results. So it does not have to scan again, what makes it much faster. If you still want to
    perform a new scan (maybe because new devices were connected), just set the argument ``rescan``
    to ``True``.

- | ``find_devices(...)``
  | Lists all available devices of the corresponding type, that match the filters passed to the
    function.
  | Here, the results are cached, too. To perform a rescan, use the ``rescan``-parameter. As filters
    you can use all attributes of the corresponding ``Device``-class, e.g. ``address``, ``serial``
    or ``mac_address``.

The internal implementation of the specific USB and LAN scanners differ depending on the platform.
Currently there are different implementations for Windows and Linux. Nevertheless, you do not have
to worry about this because you will automatically get the correct class when importing it from
``device_manager`` or ``device_manager.scanner``. Then, the imports are redirected either to
``device_manager.scanner._win32`` or ``device_manager.scanner._linux``.


General device scanner
^^^^^^^^^^^^^^^^^^^^^^

The general device scanner is represented by the class ``DeviceScanner``. It can be used just like
the specific device scanners for USB and LAN devices. But it is able to do a bit more.

The ``DeviceScanner`` is also a dictionary containing all specific device scanners. So you can use
the ``__getitem__``-operator to use one of the specific device scanners. Or you just call the
functions ``list_devices`` or ``find_devices`` directly on the ``DeviceScanner``-object. This would
automatically forward the call to each underlying device scanner. So the ``DeviceScanner`` can
search devices on all supported interfaces.


NMAP functionality
^^^^^^^^^^^^^^^^^^

For better scan results the ``LANDeviceScanner`` optionally uses *nmap*. This is a external software
that is used to scan the network for connected devices. Its functions are available via
``LANDeviceScanner.nmap``. If *nmap* is not installed or could not be found, it will not work. If
*nmap* is installed correctly and working, this will be indicated by the property ``valid``. If it
is ``True`` everything is fine. If not, the *nmap* functionality is not available. Then you should
try to install *nmap* and *python-nmap* as already mentioned in the section
:ref:`Getting Started <getting-started>`.


Device manager
--------------

The master class of this project is the ``DeviceManager``. It is used to store ``Device``s by
user-defined names, because it works like a dictionary. Additionally, it uses a general
``DeviceScanner`` to keep the device-addresses up-to-date and to search for the device's properties.
So if you want to add a device to the ``DeviceManager``, you can just add the device's address and
the device manager automatically searches for this address and adds the corresponding ``Device``
into its storage.

To save the stored ``Device``s persistently, you can also serialize the device manager to a
JSON-file. This can be done with the functions ``save`` and ``load``. Or if, you do not have a
``DeviceManager``-object, yet, you can use the context-manager-function ``load_device_manager``.
This creates a ``DeviceManager``-object, loads it from a file and optionally saves it, after you are
finished with using it.


Not enough information?
-----------------------

Have a look at our :ref:`examples <examples>`.
