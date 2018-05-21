.. iottly-sdk documentation master file, created by
   sphinx-quickstart on Sat Feb  3 16:35:48 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Python SDK iottly
======================================

Installation
--------------------------
If you are using Python 3.4.x make sure to install at least version
**1.0.1** of the **iottly-sdk**


Installing using pip (recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

  pip3 install https://github.com/tomorrowdata/iottly-sdk-python/archive/1.0.1.tar.gz

Installing using setuptools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

  wget -O iottly-sdk-python-1.0.1 https://github.com/tomorrowdata/iottly-sdk-python/archive/1.0.1.tar.gz
  tar -xzf iottly-sdk-python-1.0.1 -C /tmp
  cd /tmp/iottly-sdk-python-1.0.1
  python3 setup.py install


Classes
--------------------------

.. currentmodule:: iottly_sdk.iottly
.. autoclass:: IottlySDK
    :members: subscribe, start, send


.. toctree::
   :maxdepth: 2
   :caption: Contents:
