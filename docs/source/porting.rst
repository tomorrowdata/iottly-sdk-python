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

This interface is provided by versions of the **iottly agent**  `>= 1.6.3`.

Using this interface an SDK can communicate bi-directionally with the agent
via a shared Unix domain socket.

Communication protocol
~~~~~~~~~~~~~~~~~~~~~~

Once the **sdk** is connected to the **iottly agent**
it *must* send a connected status signal message.
In this message, the **sdk** identifies must identify
the application passing an user-provided name.

After sending this start-up message the **sdk** *must* listen
to signal or data message coming from the **agent**.

The **sdk** could receive (if connected to an **agent** `>= 1.8.0`) an
`sdkinit` signal message from the **agent** containing the version of the
**agent**. This information can be used asynchronously to adapt the
communication protocol between **sdk** and **agent** to the most recent
protocol understood by both.
Until this message is not received, the **sdk** must assume a connection with
an **agent** `< 1.8.0` and must behave accordingly.

The **sdk** should allow the user to send messages to iottly.
The **sdk** can also allow the user to send messages to
a particular channel on iottly.

The **sdk** should allow the user to invoke the *user-defined* scripts available
on the agent. If implemented, the **sdk** must ensure that this invocation
happens without blocking in the case of a disconnected **agent**.

These messages are written to the socket with the JSON encoding
described in the next section.

Payload specs
~~~~~~~~~~~~~~~~~~~~~~

All the exchanged payloads are JSON encoded with the UTF-8 charset.

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
      "sdkclient": {
        "name": "<String>",
        "status": "connected",
        "version": "<Maj.Min.Patch>"
      }
    }
  }

or

.. code-block:: json

  {
    "signal": {
      "sdkclient": {
        "name": "<String>",
        "status": "disconnected"
      }
    }
  }

- Forwarding of **errors** to iottly

.. code-block:: json

  {
    "signal": {
      "sdkclient": {
        "name": "<String>",
        "error": {}
      }
    }
  }

- Forwarding **data** to iottly

.. code-block:: json

  {
    "data": {
      "sdkclient": {
        "name": "<String>"
      },
      "payload": {}
    }
  }

- Forwarding **data** to iottly with a specific **channel**

.. code-block:: json

  {
    "data": {
      "sdkclient": {
        "name": "<String>"
      },
      "payload": {},
      "channel": "<String>"
    }
  }

- Calling **user-defined script** on the **iottly agent**

.. code-block:: json

  {
    "signal": {
      "sdkclient": {
        "name": "<String>",
        "call": {
          "<cmd_name>": {}
        }
      }
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

.. note::
  The `started` and `stopped` statuses are not received
  from the **iottly agent** but generated internally by
  the SDK.

- Agent version (semantic version number)

.. code-block:: json

  {
    "signal": {
      "sdkinit": {
        "version": "<Maj.Min.Patch>"
      }
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

- Version 1.3.0:
    - Adds SDK `version` to the `connected` status signal sent by the SDK
      at start-up.
    - Adds `sdkinit` signal sent by the agent to communicate its version
      to an SDK client.
    - Adds payload to type to call user-defined script on the agent from the SDK.
