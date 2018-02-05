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
                msg_buf[:] = next_buf , msg_buf[i+1:]
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

    def test_receiving_stopping_signal_from_server(self):
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
        self.assertEqual(3, agent_status_cb.call_count)
        sdk.stop()

    def test_sending_msg_to_agent(self):
        cb_called = multiprocessing.Event()
        def read_msg(s):
            msg_buf = []
            msg = read_msg_from_socket(s,msg_buf)
            self.assertEqual('{"data": {"payload": "test data"}}', msg.decode())
            cb_called.set()
        server = UDSStubServer(self.socket_path, on_connect=read_msg)
        server.start()
        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.start()
        sdk.send({'payload': 'test data'})
        try:
            cb_called.wait(1.0)
            self.assertTrue(cb_called.is_set())
        except TimeoutError:
            self.fail('Server doesn\'t received any connection')
        finally:
            sdk.stop()
            server.stop()
