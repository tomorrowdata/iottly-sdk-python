
import six

import os
import socket
import time
from functools import wraps
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

        max_buffered_msgs (int):
            the maximum number of messages buffered before.

        on_agent_status_changed (func, optional):
            callback to receive notification on the iottly agent status.

        on_connection_status_changed (func, optional):
            callback to receive notification on the
            iottly agent connection status.
    """

    def __init__(self, name,
                 socket_path='/var/run/iottly.com-agent/sdk/iottly_sdk_socket',
                 max_buffered_msgs=10,
                 on_agent_status_changed=None,
                 on_connection_status_changed=None):
        """Init IottlySDK
        """
        self._name = str(name)
        self._socket_path = socket_path
        self._max_buffered_msgs = max_buffered_msgs
        self._on_agent_status_changed_cb = self._wrapped_cb_execution(on_agent_status_changed)
        self._on_connection_status_changed_cb = self._wrapped_cb_execution(on_connection_status_changed)

        # Threads references
        self._consumer_t = None
        self._drainer_t = None
        self._connection_t = None

        # The queue holding the window buffer for incoming messages
        # up to self._max_buffered_msgs messages
        self._buffer = Queue(maxsize=self._max_buffered_msgs)
        self._buffer_full = Condition()

        # Conditions and state mgmt
        self._socket_state_lock = Lock()
        self._connected_to_agent = Condition(self._socket_state_lock)
        self._disconnected_from_agent = Event()
        # Indicate if there is a link to the iottly agent
        self._agent_linked = False
        # The unix socket to communicate with the iottly agent
        self._socket = None

        # Pre-computed messages (JSON strings)
        # NOTE literal curly braces are double-up to use format spec-language
        self._app_start_msg = \
            '{{"signal": {{"sdkclient": {{"name": "{}", "status": "connected"}}}}}}\n'.format(self._name).encode()
        # NOTE Since the data msg template will be later proessed with format
        # the curly brace are quadruplicated {{{{ -> {{ -> {
        self._data_msg = '{{{{"data": {{{{"sdkclient": {{{{"name": "{}"}}}}, "payload": {}}}}}}}}}\n'.format(self._name, '{}')
        self._err_msg = '{{{{"signal": {{{{"sdkclient": {{{{"name": "{}", "error": {}}}}}}}}}}}}}\n'.format(self._name, '{}')

        # Lookup-table (cmd_type -> callback)
        # Store the callback function for a particular message type
        self._cmd_callbacks = {}

        self._sdk_stopped = Event()


    def send(self, msg):
        """Sends a message to iottly.

        Use this method for sending a message to iottly through
        the **iottly agent** running on the same machine.

        If the agent is unavailable the message is buffered internally.
        At most `max_buffered_msgs` messages will be kept in the internal
        buffer, after this limit is reached the older messages will be
        discarded.

        .. seealso:: The `max_buffered_msgs` parameter is configurable during the SDK initialization.

        Args:
            msg (`dict`):
                The data to be sent. The `dict` should be JSON-serializable.

        Raises:
            TypeError:
                `send` was invoked with a non `dict` argument.
            ValueError:
                `send` was invoked with a non JSON-serializable `dict`.
        """
        if not isinstance(msg, dict):
            err = 'msg must be a dict but {} was given.'.format(type(msg))
            raise TypeError(err)

        try:
            json.dumps(msg)
        except TypeError as e:
            raise ValueError('Given msg is not JSON-serializable.')

        payload = (msg, False)  # denote a data payload
        try:
            self._buffer.put(payload, False)  # en-queue the msg non-blocking
        except Full:
            # Notify the buffer flusher that the buffer is full
            # If the buffer dimension is correctly set
            # this should happend only if:
            # - the iottly agent is disconnected from the network
            # - the sdk is disconnected from the iottly agent
            with self._buffer_full:
                self._buffer_full.notify()
            self._buffer.put(payload) # en-queue the msg blocking


    def subscribe(self, cmd_type, callback):
        """Subscribe to specific command received from the iottly-agent.

        After subscribing a callback for a command type, the iottly SDK is
        notified each time the **iottly agent** receives a message for the
        particular command.

        The `callback` will be invoked with a dict containing the
        command parameters.

        .. note:: If you call `subscribe` with a `cmd_type` already registered the callback is overwritten.

        Args:
            `cmd_type` (`str`):
                The string denoting a particular type of command.
            `callback` (func or callable):
                The callback invoked when a message of type `cmd_type` is received from the **iottly agent**

        Raises:
            TypeError:
                The method was invoked with an argument of wrong type.
        """
        if not isinstance(cmd_type, six.string_types):
            # Typecheck cmd_type (python2 compatible)
            err = 'cmd_type must be a string but {} was given.'.format(type(cmd_type))
            raise TypeError(err)

        if not six.callable(callback):
            # Typecheck cmd_type (python2 compatible)
            err = 'callback must be a callable but {} was given.'.format(type(cmd_type))
            raise TypeError(err)

        self._cmd_callbacks[cmd_type] = self._wrapped_cb_execution(callback)


    def start(self):
        """Connect to the iottly agent.
        """
        # Start the thread that receive messages from the iottly agent
        self._receiver_t = Thread(target=self._receive_msgs_from_agent,
                                    name='receiver_t')
        self._receiver_t.daemon = True
        self._receiver_t.start()
        # Start the thread that keep the buffer size at bay
        self._drainer_t = Thread(target=self._drain_buffer, name='drainer_t')
        self._drainer_t.daemon = True
        self._drainer_t.start()
        # Start the thread that send messages to the iottly agent
        self._consumer_t = Thread(target=self._consume_buffer, name='sender_t')
        self._consumer_t.daemon = True
        self._consumer_t.start()
        # Start the thread that connect the iottly agent
        self._connection_t = Thread(target=self._connect_to_agent,
                                    name='connection_t')
        self._connection_t.daemon = True
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
                # Send notification of connected app to the iottly agent
                self._buffer.put((self._app_start_msg, True))  # Signalling
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
                        continue  # re-acquire the socket (None)
                try:
                    data, is_signal = msg
                    if is_signal:
                        # Signalling data is already JSON formatted and
                        # netwrok encoded (bytes)
                        payload = data
                    else:
                        payload = self._msg_serialize(data)
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
                # Check the exit condition on resume
                if self._sdk_stopped.is_set():
                    break
                # None msg received -> Notify disconnection
                with self._socket_state_lock:
                    if not self._disconnected_from_agent.is_set():
                        self._disconnected_from_agent.set()
                # Wait for the connection to be re established
                with self._connected_to_agent:
                    self._connected_to_agent.wait()

    def _process_msg_from_agent(self, msg):
        try:
            msg = json.loads(msg)
        except ValueError:
            # if we receive an invalid message -> skip it
            return
        if 'signal' in msg:
            self._handle_signals_from_agent(msg['signal'])
        elif 'data' in msg:
            self._handle_cmd_from_agent(msg['data'])
        else:
            # TODO handle invalid msg. Disconnect?
            return

    def _handle_signals_from_agent(self, signal):
        if 'agentstatus' in signal:
            status = signal['agentstatus']  # TODO validate status
            self._on_agent_status_changed_cb(status)
        elif 'connectionstatus' in signal:
            status = signal['connectionstatus']  # TODO validate status
            self._on_connection_status_changed_cb(status)
        else:
            # TODO handle invalid signal
            return

    def _handle_cmd_from_agent(self, cmd):
        # Ensure there is a top-level key
        if len(cmd) == 1:
            # get the command type
            cmd_type = None
            for k in six.iterkeys(cmd):
                cmd_type = k
            # execute the registered cb (if any)
            try:
                cb = self._cmd_callbacks[cmd_type]
                # Execute callback
                cb(cmd[cmd_type])
            except KeyError:
                pass
        else:
            # TODO handle invalid commands
            pass

    def _msg_serialize(self, msg):
        # Prepare message to be sent on a socket
        return self._data_msg.format(json.dumps(msg)).encode()

    def _wrapped_cb_execution(self, f):
        """Wrap callback execution and send error to agent.
        """
        if f is None:
            return None

        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                f(*args, **kwargs)
            except Exception as exc:
                exc_dump = json.dumps({
                    'type': exc.__class__.__name__,
                    'msg': str(exc)
                })
                # Format signal message
                exc_msg = (self._err_msg.format(exc_dump).encode(), True)
                self._buffer.put(exc_msg)  # En-quque msg blocking

        return wrapper

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
