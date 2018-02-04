import unittest
from unittest.mock import Mock

import os
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

    def test_sending_msg_to_agent(self):
        cb_called = multiprocessing.Event()
        def read_msg(s):
            msg_buf = []
            msg = read_msg_from_socket(s,msg_buf)
            self.assertEqual('test data', msg.decode())
            cb_called.set()
        server = UDSStubServer(self.socket_path, on_connect=read_msg)
        server.start()
        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.start()
        sdk.send('test data')
        try:
            cb_called.wait(1.0)
            self.assertTrue(cb_called.is_set())
        except TimeoutError:
            self.fail('Server doesn\'t received any connection')
        finally:
            sdk.stop()
            server.stop()
