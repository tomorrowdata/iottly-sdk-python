.. iottly-sdk documentation master file, created by
   sphinx-quickstart on Sat Feb  3 16:35:48 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Python SDK iottly
======================================

Installation
--------------------------

- If you are using Python 3.4.x install **iottly-sdk** >= **1.1.0**
- If you are using Python 2.7.x install **iottly-sdk** >= **1.2.0**


Installing using pip (recommended)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- On **Python 3**
  ::

    sudo pip3 install https://github.com/tomorrowdata/iottly-sdk-python/archive/1.2.0.tar.gz

- On **Python 2.7**
  ::

    sudo pip install https://github.com/tomorrowdata/iottly-sdk-python/archive/1.2.0.tar.gz


or using setuptools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
::

  wget -O iottly-sdk-python-1.2.0.tar.gz https://github.com/tomorrowdata/iottly-sdk-python/archive/1.2.0.tar.gz
  tar -xzf iottly-sdk-python-1.2.0.tar.gz -C /tmp
  cd /tmp/iottly-sdk-python-1.2.0

- On Python 3
  ::

    sudo python3 setup.py install

- On Python 2.7
  ::

    sudo python2.7 setup.py install


Classes
--------------------------

.. currentmodule:: iottly_sdk.iottly
.. autoclass:: IottlySDK
    :members: subscribe, start, send


.. toctree::
   :maxdepth: 2
   :caption: Contents:

Chnagelog
--------------------------

.. versionadded:: 1.1.0
   Adds support for Python 3.4

.. versionadded:: 1.2.0
  Adds support for Python 2.7
