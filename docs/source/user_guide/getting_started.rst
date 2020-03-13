.. _getting-started:

Getting Started
===============


Requirements
------------

To use the DeviceManager, you will need a working installation of **Python 3.x** (at least version
3.6) and **pip**. Depending on your platform, you will need to meet a few requirements concerning
both your python environment and system. The requirements for the Python environment are
automatically taken into account during installation, but there are still some external
dependencies.


Windows
^^^^^^^

On Windows there are **no mandatory requirements** to consider.

If you want to use the *nmap*-functionality, you need to make sure, it is installed. If not, you can
download the latest version of *nmap* from `this link <https://nmap.org/download.html#windows>`_.

Alternatively, you can also use *Chocolately* to install *nmap*:

.. code-block::

   > choco install nmap


Linux
^^^^^

If you are using a Linux system, you eventually need to install the *arp*-command. This is needed by
the ``LANDeviceScanner`` for reading out the ARP-cache, which contains a mapping of IP-addresses to
MAC-addresses. The *arp*-command is part of the package ``net-tools``. On Debian-based systems you
can install it by using the following command:

.. code-block::

   $ sudo apt-get install net-tools

Additionally you may be interested in using the *nmap*-functionality, which is optionally. On
Debian-based systems you can install *nmap* with:

.. code-block::

   $ sudo apt-get install nmap


Installation
------------

To install the DeviceManager, perform the following steps:

1. Clone the DeviceManager-repository from `GitHub <https://github.com/zea2/DeviceManager>`_

.. code-block::

   $ git clone https://github.com/zea2/DeviceManager

2. Navigate to the cloned repository

.. code-block::

   $ cd DeviceManager

3. Install the DeviceManager

   - To install the DeviceManager, you need to know if you want to use the *nmap*-functionality. If
     not, install the package like this:

     .. code-block::

        $ pip3 install .

   - If you want to use *nmap* to get better results when searching for network devices, use this:

     .. code-block::

        $ pip3 install .[nmap]


Getting started
---------------

Have a look at the :ref:`project's concepts <concepts>` or browse the :ref:`example notebooks
<examples>`.
