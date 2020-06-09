
Python SDK iottly
======================================

Python module handling interaction with the `iottly
<https://iottly.com/>`_ agent from third-party applications.

|

Briefly, the registered app could:
    - Sends messages to iottly
    - Subscribes to specifics commands received from the iottly-agent
    - Calls a Python snippet in the user-defined scripts of the attached agent
    - Registers callbacks on specifics iottly-agent notification

|

How it works:

.. image:: _static/Agent_SDK.jpg

|

Example snippet:

.. literalinclude:: myfirstiottlyapp.py

|

.. toctree::
    :caption: Table of Contents
    :maxdepth: 1

    installation
    API
    porting
    changelog
