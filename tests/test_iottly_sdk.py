import unittest
from unittest.mock import Mock, call

import os
import time
import tempfile
import multiprocessing

from stubs.agent_server import UDSStubServer

from iottly_sdk import iottly


def read_msg_from_socket(socket, msg_buf):
    go_on = True
    while go_on:
        for i, b in enumerate(msg_buf):
            chunck, splitted, next_buf = b.partition(b'\n')
            if splitted:
                # we have a new message
                msg = b''.join(msg_buf[:i]) + chunck
                if next_buf:
                    # msg_buf[:] = next_buf, * msg_buf[i+1:]
                    # Compatobility with Py 3.4
                    tmp = msg_buf[i+1:]
                    msg_buf[:] = next_buf
                    msg_buf[i+1:] = tmp
                else:
                    msg_buf[:] = msg_buf[i+1:]
                return msg
        buf = socket.recv(1024)
        if buf == b'':
            go_on = False
        else:
            msg_buf.append(buf)



class IottlySDK(unittest.TestCase):

    def setUp(self):
        self.sock_dir = tempfile.TemporaryDirectory()
        self.socket_path = socket_path = os.path.join(self.sock_dir.name, 'test_socket')

    def tearDown(self):
        self.sock_dir.cleanup()

    def test_connection_with_running_server(self):
        server_started = multiprocessing.Event()
        cb_called = multiprocessing.Event()
        def test_connection(s):
            msg_buf = []
            msg = read_msg_from_socket(s,msg_buf)
            self.assertEqual('{"signal": {"sdkclient": {"name": "testapp", "status": "connected"}}}', msg.decode())
            cb_called.set()
        server = UDSStubServer(self.socket_path, on_bind=server_started.set, on_connect=test_connection)
        server.start()
        try:
            server_started.wait(2)
        except TimeoutError:
            pass
        self.assertTrue(os.path.exists(self.socket_path))
        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.start()
        try:
            cb_called.wait(1.0)
            self.assertTrue(cb_called.is_set())
        except TimeoutError:
            self.fail('Server doesn\'t received any connection')
        finally:
            sdk.stop()
            server.stop()

    def test_connection_callback(self):
        server_started = multiprocessing.Event()
        client_connected = multiprocessing.Event()
        def on_connect(s):
            client_connected.set()
        server = UDSStubServer(self.socket_path, on_bind=server_started.set, on_connect=on_connect)
        server.start()
        try:
            server_started.wait(2.0)
        except TimeoutError:
            self.fail('cannot start server')
        agent_status_cb = Mock()

        sdk = iottly.IottlySDK('testapp', self.socket_path,
                                on_agent_status_changed=agent_status_cb)
        sdk.start()

        client_connected.wait(2.0)
        server.stop()
        sdk.stop()
        agent_status_cb.assert_has_calls([call('started'), call('stopped')])

    def test_receiving_stopping_signal_from_agent(self):
        server_started = multiprocessing.Event()
        client_connected = multiprocessing.Event()
        def on_connect(s):
            s.send(b'{"signal": {"agentstatus": "stopping"}}\n')
            client_connected.set()
        server = UDSStubServer(self.socket_path, on_bind=server_started.set, on_connect=on_connect)
        server.start()
        try:
            server_started.wait(2.0)
        except TimeoutError:
            self.fail('cannot start server')
        agent_status_cb = Mock()

        sdk = iottly.IottlySDK('testapp', self.socket_path,
                                on_agent_status_changed=agent_status_cb)
        sdk.start()
        client_connected.wait(2.0)
        server.stop()

        time.sleep(0.6)  # give some time
        agent_status_cb.assert_has_calls([call('started'), call('stopping'), call('stopped')])
        sdk.stop()

    def test_receiving_connection_status_signalling_from_agent(self):
        server_started = multiprocessing.Event()
        client_connected = multiprocessing.Event()
        def on_connect(s):
            s.send(b'{"signal": {"connectionstatus": "disconnected"}}\n')
            s.send(b'{"signal": {"connectionstatus": "connected"}}\n')
            client_connected.set()
        server = UDSStubServer(self.socket_path, on_bind=server_started.set, on_connect=on_connect)
        server.start()
        try:
            server_started.wait(2.0)
        except TimeoutError:
            self.fail('cannot start server')
        conn_status_cb = Mock()

        sdk = iottly.IottlySDK('testapp', self.socket_path,
                                on_connection_status_changed=conn_status_cb)
        sdk.start()
        client_connected.wait(2.0)
        server.stop()

        time.sleep(0.6)  # give some time
        conn_status_cb.assert_has_calls([call('disconnected'),call('connected')])
        sdk.stop()

    def test_sending_msg_to_agent(self):
        cb_called = multiprocessing.Event()
        def read_msg(s):
            msg_buf = []
            _ = read_msg_from_socket(s,msg_buf) # 1st msg in signal
            msg = read_msg_from_socket(s,msg_buf)
            self.assertEqual('{"data": {"sdkclient": {"name": "testapp"}, "payload": {"test_metric": "test data"}}}', msg.decode())
            cb_called.set()
        server = UDSStubServer(self.socket_path, on_connect=read_msg)
        server.start()
        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.start()
        time.sleep(0.7)
        sdk.send({'test_metric': 'test data'})
        try:
            cb_called.wait(1.0)
            self.assertTrue(cb_called.is_set())
        except TimeoutError:
            self.fail('Server doesn\'t received any connection')
        finally:
            sdk.stop()
            server.stop()

    def test_registering_callback_for_message_type(self):
        server_started = multiprocessing.Event()
        client_connected = multiprocessing.Event()
        def on_connect(s):
            s.send(b'{"data": {"echo":{"content":"IOTTLY hello world!!!!"}}}\n')
            client_connected.set()
        server = UDSStubServer(self.socket_path, on_bind=server_started.set, on_connect=on_connect)
        server.start()
        try:
            server_started.wait(2.0)
        except TimeoutError:
            self.fail('cannot start server')
        cmd_cb = Mock()

        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.subscribe('echo', cmd_cb)
        sdk.start()
        client_connected.wait(2.0)
        server.stop()

        time.sleep(0.6)  # give some time
        try:
            cmd_cb.assert_called_once_with({'content':'IOTTLY hello world!!!!'})
        finally:
            sdk.stop()

    def test_callback_invoked_only_if_registered(self):
        server_started = multiprocessing.Event()
        client_connected = multiprocessing.Event()
        def on_connect(s):
            s.send(b'{"data": {"non_echo":{"content":"IOTTLY hello world!!!!"}}}\n')
            client_connected.set()
        server = UDSStubServer(self.socket_path, on_bind=server_started.set, on_connect=on_connect)
        server.start()
        try:
            server_started.wait(2.0)
        except TimeoutError:
            self.fail('cannot start server')
        cmd_cb = Mock()

        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.subscribe('echo', cmd_cb)
        sdk.start()
        client_connected.wait(2.0)
        server.stop()

        time.sleep(0.6)  # give some time
        try:
            cmd_cb.assert_not_called()
        finally:
            sdk.stop()

    def test_handling_exception_in_callbacks(self):
        server_started = multiprocessing.Event()
        client_connected = multiprocessing.Event()
        def on_connect(s):
            s.send(b'{"data": {"echo":{"content":"IOTTLY hello world!!!!"}}}\n')
            client_connected.set()
            msg_buf = []
            msg = read_msg_from_socket(s,msg_buf)
            self.assertEqual('{"signal": {"sdkclient": {"name": "testapp", "error": {"type": "ValueError", "msg": "exception in cb"}}}}', msg.decode())
        server = UDSStubServer(self.socket_path, on_bind=server_started.set, on_connect=on_connect)
        server.start()
        try:
            server_started.wait(2.0)
        except TimeoutError:
            self.fail('cannot start server')
        cmd_cb = Mock(side_effect=ValueError('exception in cb'))

        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.subscribe('echo', cmd_cb)
        sdk.start()
        client_connected.wait(2.0)
        server.stop()

        time.sleep(0.6)  # give some time
        try:
            self.assertEqual(1, cmd_cb.call_count)
        finally:
            sdk.stop()
