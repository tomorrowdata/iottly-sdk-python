
import six

import os
import socket
from threading import Thread, Condition
from queue import Queue, Full


class IottlySDK:
    """Class handling interactions with the iottly-agent

    ...

    Args:
        name (str):
            an identifier for the connected application.
        socket_path (str):
            the path to the unix-socket exposed by the iottly agent.

        max_bufferd_msgs (int):
            the maximum number of messages buffered before.

        on_agent_status_changed (func, optional):
            callback to receive notification on the iottly agent status.

        on_connection_status_changed (func, optional):
            callback to receive notification on the 
            iottly agent connection status.
    """

    def __init__(self, name,
                 socket_path='/var/run/iottly/iottly_sdk_socket',
                 max_buffered_msgs=10,
                 on_agent_status_changed=None,
                 on_connection_status_changed=None):
        """Init IottlySDK
        """
        self._name = name
        self._socket_path = socket_path
        self._max_buffered_msgs = max_buffered_msgs
        self._on_agent_status_changed_cb = on_agent_status_changed
        self._on_connection_status_changed_cb = on_agent_status_changed

        # Threads references
        self._consumer_t = None
        self._drainer_t = None
        self._connection_t = None

        # The queue holding the window buffer for incoming messages
        # up to self._max_buffered_msgs messages
        self._buffer = Queue(maxsize=self._max_buffered_msgs)

        # Conditions and state mgmt
        self._connected_to_agent = Condition()
        self._disconnected_from_agent = Condition()
        # Indicate if there is a link to the iottly agent
        self._active = False
        # The unix socket to communicate with the iottly agent
        self._socket = None

        self._buffer_full = Condition()

        self._sdk_running = True


    def send(self, msg):
        """Sends a message to iottly.

        Use this method for sending a message to iottly through
        the **iottly agent** running on the same machine.

        If the agent is unavailable the message is buffered internally.
        At most 

        Args:
            msg (str): The string to be sent.
        """
        try:
            self._buffer.put(msg, False)  # en-queue the msg non-blocking
        except Full:
            # Notify the buffer flusher that the buffer is full
            # If the buffer dimension is correctly set
            # this should happend only if:
            # - the iottly agent is disconnected from the network
            # - the sdk is disconnected from the iottly agent
            self._buffer_full.acquire()
            self._buffer_full.notify()
            self._buffer_full.release()
            self._buffer.put(msg) # en-queue the msg blocking


    def subscribe(self, cmd_type, callback):
        """Subscribe to specific command received from the iottly-agent.
        """
        pass

    def start(self):
        """Connect to the iottly agent.
        """
        # Start the thread that receive messages from the iottly agent
        # self._thread = Thread(target=)

        # Start the thread that keep the buffer size at bay
        self._drainer_t = Thread(target=self._drain_buffer)
        self._drainer_t.start()
        # Start the thread that send messages to the iottly agent
        self._consumer_t = Thread(target=self._consume_buffer)
        self._consumer_t.start()
        # Start the thread that connect the iottly agent
        self._connection_t = Thread(target=self._connect_to_agent)
        self._connection_t.start()

    def stop():
        """Convenience method to stop the sdk threads and perform cleanup
        """
        self._sdk_running = False
        # Notify the connection thread
        self._disconnected_from_agent.notify()
        self._connection_t.join()

        self._buffer_full.notify()
        self._drainer_t.join()

        

    # ======================================================================== #
    # =========================== Private Methods ============================ #
    # ======================================================================== #

    def _connect_to_agent(self):
        """Try to create a connection to the iottly agent SDK server.
        """
        while self._sdk_running:
            with self._connected_to_agent:
                # # TODO check this in the init
                # if os.path.exists(self._socket_path):
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    s.connect(self._socket_path)
                except ConnectionRefusedError:
                    continue
                except OSError as e:
                    continue
                self._socket = s
                self._active = True
                self._on_agent_status_changed_cb('started')
                self._connect_to_agent.notifyAll()
            # Wait until the unix socket is broken
            with self._disconnected_from_agent:
                self._disconnected_from_agent.wait()

    def _consume_buffer(self):
        """Consume a message from the internal buffer and try to send it.
        """
        while self._sdk_running:
            with self._connected_to_agent:
                connected = self._active
                socket = self._socket

            if connected:
                msg = self._buffer.get()  # de-queue a msg blocking
                sent = False
                while not sent:
                    try:
                        # TODO here we should serialize the msg
                        socket.sendall(msg.encode())
                    except OSError:
                        # Notify disconnection to connection mgmt thread
                        with self._disconnected_from_agent:
                            self._disconnected_from_agent.notify()
                        # Wait for the connection to be re established
                        with self._connected_to_agent:
                            self._connected_to_agent.wait()
                    # the message was forwarded
                    sent = True
            else:
                # Wait for the connection to be re established
                with self._connected_to_agent:
                    self._connected_to_agent.wait()

    def _drain_buffer(self):
        while self._sdk_running:
            with self._buffer_full:
                self._buffer_full.wait()
                if self._buffer.full():
                    # Consume and discard a message
                    try:
                        self._buffer.get(False)
                    except Empty:
                        pass
