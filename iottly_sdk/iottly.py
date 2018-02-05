
import six

import os
import socket
import time
from threading import Thread, Condition, Event, Lock
from queue import Queue, Full
import json

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
        self._socket_state_lock = Lock()
        self._connected_to_agent = Condition(self._socket_state_lock)
        self._disconnected_from_agent = Event()
        # Indicate if there is a link to the iottly agent
        self._agent_linked = False
        # The unix socket to communicate with the iottly agent
        self._socket = None

        self._buffer_full = Condition()

        self._sdk_stopped = Event()


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
            with self._buffer_full:
                self._buffer_full.notify()
            self._buffer.put(msg) # en-queue the msg blocking


    def subscribe(self, cmd_type, callback):
        """Subscribe to specific command received from the iottly-agent.
        """
        pass

    def start(self):
        """Connect to the iottly agent.
        """
        # Start the thread that receive messages from the iottly agent
        self._receiver_t = Thread(target=self._receive_msgs_from_agent,
                                    name='receiver')
        self._receiver_t.start()
        # Start the thread that keep the buffer size at bay
        self._drainer_t = Thread(target=self._drain_buffer, name='drainer')
        self._drainer_t.start()
        # Start the thread that send messages to the iottly agent
        self._consumer_t = Thread(target=self._consume_buffer, name='consumer')
        self._consumer_t.start()
        # Start the thread that connect the iottly agent
        self._connection_t = Thread(target=self._connect_to_agent,
                                    name='connection')
        self._connection_t.start()

    def stop(self):
        """Convenience method to stop the sdk threads and perform cleanup
        """
        self._sdk_stopped.set()
        # Wake the connection thread so it can exit properly
        self._disconnected_from_agent.set()
        self._connection_t.join()
        # Wake the drainer thread so it can exit properly
        with self._buffer_full:
            self._buffer_full.notify()
        self._drainer_t.join()
        # Wake up consumer thread waiting on empty buffer
        self._buffer.put(None, False)
        # Wake up the consumer and receiver threads so they can exit properly
        with self._connected_to_agent:
            self._connected_to_agent.notifyAll()
        self._consumer_t.join()
        self._receiver_t.join()


    # ======================================================================== #
    # =========================== Private Methods ============================ #
    # ======================================================================== #

    def _connect_to_agent(self):
        """Try to create a connection to the iottly agent SDK server.
        """
        while not self._sdk_stopped.is_set():
            with self._connected_to_agent:
                # # TODO check this in the init
                # if os.path.exists(self._socket_path):
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    s.connect(self._socket_path)
                except ConnectionRefusedError:
                    s.close()
                    time.sleep(0.2)
                    continue
                except OSError as e:
                    s.close()
                    time.sleep(0.2)
                    continue
                self._socket = s
                self._agent_linked = True
                # Exec callback
                if self._on_agent_status_changed_cb:
                    self._on_agent_status_changed_cb('started')
                # TODO send registration msg to iottly agent
                # Notify the other threads that require the connection
                self._disconnected_from_agent.clear()
                self._connected_to_agent.notifyAll()
            # Wait until the unix socket is broken
            # and the event _disconnected_from_agent is fired
            self._disconnected_from_agent.wait()
            with self._connected_to_agent:
                # Set the disconnected state flag
                self._agent_linked = False
                if self._socket:
                    self._socket.close()
                self.socket = None

            # Exec callback
            if self._on_agent_status_changed_cb:
                self._on_agent_status_changed_cb('stopped')
        # Exit

    def _consume_buffer(self):
        """Consume a message from the internal buffer and try to send it.
        """
        while not self._sdk_stopped.is_set():
            msg = self._buffer.get()  # de-queue a msg blocking
            if msg is None:
                break  # None is pushed to wake-up the thread for exit
            # Try sending the message
            sent = False
            while not sent:
                with self._connected_to_agent:
                    # Get the socket
                    socket = self._socket
                    if not socket:
                        self._connected_to_agent.wait()
                        # Check the exit condition on resume
                        if self._sdk_stopped.is_set():
                            break
                try:
                    payload = self._msg_serialize(msg)
                    socket.sendall(payload)
                    # the message was forwarded
                    sent = True
                except OSError:
                    # Wait for the connection to be re established
                    with self._connected_to_agent:
                        self._connected_to_agent.wait()
                    # Check the exit condition on resume
                    if self._sdk_stopped.is_set():
                        break

    def _drain_buffer(self):
        """Keep the internal buffer at bay.
        """
        while not self._sdk_stopped.is_set():
            with self._buffer_full:
                self._buffer_full.wait()
                if self._buffer.full():
                    # Consume and discard a message
                    try:
                        self._buffer.get(False)
                    except Empty:
                        pass
        logging.info('drainer exiting')

    def _receive_msgs_from_agent(self):
        """Receive messages/signals from the iottly agent
        """
        msg_buf = []
        while not self._sdk_stopped.is_set():
            with self._socket_state_lock:
                socket = self._socket
            if not socket:
                # Wait for the connection to be re established
                with self._connected_to_agent:
                    self._connected_to_agent.wait()
                # Check the exit condition on resume
                if self._sdk_stopped.is_set():
                    break
            msgs = _read_msg_from_socket(self._socket, msg_buf)
            if msgs:
                for msg in msgs:
                    # Process messages
                    self._process_msg_from_agent(msg)
            else:
                # None msg received -> Notify disconnection
                with self._socket_state_lock:
                    if not self._disconnected_from_agent.is_set():
                        self._disconnected_from_agent.set()
                # Wait for the connection to be re established
                with self._connected_to_agent:
                    self._connected_to_agent.wait()

    def _process_msg_from_agent(self, msg):
        msg = json.loads(msg)
        if 'signal' in msg:
            self._handle_signals_from_agent(msg['signal'])
        elif 'data' in msg:
            pass
        else:
            # TODO handle invalid msg. Disconnect?
            pass

    def _handle_signals_from_agent(self, signal):
        if 'agentstatus' in signal:
            status = signal['agentstatus']  # TODO validate status
            self._on_agent_status_changed_cb(status)
        else:
            # TODO handle invalid signal
            pass

    def _msg_serialize(self, msg):
        # Prepare message to be sent on a socket
        return "{}\n".format(json.dumps({'data': msg})).encode()

def _read_msg_from_socket(socket, msg_buf):
    msgs = []
    while not msgs:
        # Try to receive data from agent
        try:
            # Read one message from the socket
            buf = socket.recv(1024)
            if buf == b'':
                # Broken connection
                return None
            else:
                msg_buf.append(buf)
        except OSError:
            return None
        # Extract messages
        i = 0
        buff_dim = len(msg_buf)
        while i < buff_dim:
            current = msg_buf[i]
            chunck, splitted, next_buf = current.partition(b'\n')
            if splitted:
                # we have a new message
                msg = b''.join(msg_buf[:i]) + chunck
                if next_buf:
                    msg_buf[:] = next_buf, * msg_buf[i+1:]
                else:
                    msg_buf[:] = msg_buf[i+1:]
                # Update indexes
                i = 0
                buff_dim = len(msg_buf)
                msgs.append(msg.decode())
            else:
                i += 1  # Consider next buffered item
    # There is at least 1 complete message
    return msgs
