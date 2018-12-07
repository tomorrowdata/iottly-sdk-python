Porting
======================================

Portings of the **iottly SDK** from the Python reference implementation to
other languages are welcome!

The **iottly SDK** makes use of *Unix domain sockets* to communicates
with a local *iottly agent* daemon, so in order to port the SDK you should
be able to handle such communication mechanism from your environment.

In this document we will discuss the programming interface exposed by the
**iottly agent** for the integration of an SDK.

UDS interface
------------------------------------------

This interface is provided by the **iottly agent** since version `1.6.3`.

Using this interface an SDK can communicate bi-directionally with the agent
via a shared Unix domain socket.

Communication protocol
~~~~~~~~~~~~~~~~~~~~~~

Once the **sdk** is connected to the **iottly agent**
it *must* send a connected status signal. The **sdk** identifies
the application passing an user-provided string.

.. code-block:: json

  {
    "signal": {
      "sdkclient": "<String>",
      "status": "connected"
    }
  }


After sending this start-up message the **sdk** *must* listen
to signal or data message coming from the **agent**.

The **sdk** should allow the user to send messages to iottly.
The **sdk** can also allow the user to send messages to
a particular channel on iottly.
These messages are written to the socket with the JSON encoding
as described in the next section.

Payload specs
~~~~~~~~~~~~~~~~~~~~~~

Messages sent from the SDK to the iottly agent
+++++++++++++++++++++++++++++++++++++++++++++++

SDKs can send two types of messages to the iottly agent:

  - *signal* messages
  - *data* messages

Each type of message is denoted by the top-level key of the JSON message.

Currently supported messages:

- Status signal

.. code-block:: json

  {
    "signal": {
      "sdkclient": "<String>",
      "status": "connected | disconnected"
    }
  }

- Forwarding of **errors** to iottly

.. code-block:: json

  {
    "signal": {
      "sdkclient": "<String>",
      "error": {
        "type": "<String>",
        "msg": "<String>"
      }
    }
  }

- Forwarding **data** to iottly

.. code-block:: json

  {
    "data": {
      "sdkclient": "<String>",
      "payload": {}
    }
  }

- Forwarding **data** to iottly with a specific **channel**

.. code-block:: json

  {
    "data": {
      "sdkclient": "<String>",
      "payload": {},
      "channel": "<String>"
    }
  }

Messages received by SDK from the iottly agent
+++++++++++++++++++++++++++++++++++++++++++++++

- Connection status signal

.. code-block:: json

  {
    "signal": {
      "connectionstatus": "connected | disconnected"
    }
  }

- Agent status signal

.. code-block:: json

  {
    "signal": {
      "agentstatus": "closing"
    }
  }


- Messages from iottly or from a Python snippet running on the agent.

.. code-block:: json

  {
    "data": {
      "cmd": {
        "k": "v"
      }
    }
  }

Changelog
+++++++++++++++++++++++++++++++++++++
