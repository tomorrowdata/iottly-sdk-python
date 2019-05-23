from __future__ import absolute_import
import unittest

try:
    from unittest.mock import Mock, call
except ImportError:
    from mock.mock import Mock, call
    # Handle __name__ attribute for Mock in Python2
    _Mock = Mock
    def mock_wrapper(name='', **kwargs):
        m = _Mock(**kwargs)
        m.__name__ = name
        return m
    Mock = mock_wrapper

import os
import time
import shutil
import tempfile
import multiprocessing

from stubs.agent_server import UDSStubServer

from iottly_sdk import iottly
from iottly_sdk.errors import DisconnectedSDK, InvalidAgentVersion

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
                    msg_buf[0] = next_buf
                    msg_buf[1:] = tmp[:]
                else:
                    msg_buf[:] = msg_buf[i+1:]
                return msg
        try:
            buf = socket.recv(1024)
            if buf == b'':
                go_on = False
            else:
                msg_buf.append(buf)
        except OSError:
            go_on= False



class IottlySDK(unittest.TestCase):

    def setUp(self):
        try:
            self.sock_dir = tempfile.TemporaryDirectory()
            self.socket_path = os.path.join(self.sock_dir.name, 'test_socket')
        except AttributeError:
            # Python 2.7
            self.sock_dir = tempfile.mkdtemp()
            self.socket_path = os.path.join(self.sock_dir, 'test_socket')

    def tearDown(self):
        try:
            self.sock_dir.cleanup()
        except AttributeError:
            # Python 2.7
            shutil.rmtree(self.sock_dir)

    def wait_or_fail(self, evt, timeout=2.0, msg=''):
        """Wait timeout second for an event or fail test with msg
        """
        res = evt.wait(timeout)
        if not res:
            self.fail(msg)

    def test_connection_with_running_server(self):
        server_started = multiprocessing.Event()
        cb_called = multiprocessing.Event()
        def test_connection(s):
            msg_buf = []
            msg = read_msg_from_socket(s,msg_buf)
            exp_msg = '{"signal": {"sdkclient": {"name": "testapp", "status": "connected", "version": "%s"}}}' % iottly.__version__
            self.assertEqual(exp_msg, msg.decode())
            cb_called.set()
        server = UDSStubServer(self.socket_path, on_bind=server_started.set, on_connect=test_connection)
        server.start()
        try:
            server_started.wait(2)
        except OSError as e:
            if e.errno == errno.ETIMEDOUT:
                pass
        self.assertTrue(os.path.exists(self.socket_path))
        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.start()
        try:
            cb_called.wait(1.0)
            self.assertTrue(cb_called.is_set())
        except OSError as e:
            if e.errno == errno.ETIMEDOUT:
                self.fail('Server doesn\'t received any connection')
        finally:
            sdk.stop()
            server.stop()

    def test_get_version_from_agent(self):
        server_started = multiprocessing.Event()
        cb_called = multiprocessing.Event()
        sdk_linked = multiprocessing.Event()
        finished = multiprocessing.Event()

        def send_sdkinit_signal(s):
            s.send(b'{"signal": {"sdkinit": {"version": "1.8.0"}}}\n')
            cb_called.set()
            msg_buf = []
            read_msg_from_socket(s, msg_buf)
            finished.wait(4.0)
        server = UDSStubServer(self.socket_path, on_bind=server_started.set, on_connect=send_sdkinit_signal)
        server.start()
        self.wait_or_fail(server_started, timeout=2.0, msg='Cannot start mock server')

        def agent_status_cb(status):
            sdk_linked.set()

        sdk = iottly.IottlySDK('testapp', self.socket_path,
                                    on_agent_status_changed=agent_status_cb)
        sdk.start()
        self.wait_or_fail(cb_called, timeout=2.0, msg='Cannot sent sdkinit from server')
        self.wait_or_fail(sdk_linked, timeout=10.0, msg='Started CB not called')
        self.assertEqual('1.8.0', sdk._agent_version)
        finished.set()
        server.stop()
        sdk.stop()

    def test_connection_callback(self):
        server_started = multiprocessing.Event()
        client_connected = multiprocessing.Event()
        exit_set = multiprocessing.Event()

        def on_connect(s):
            client_connected.set()
            msg_buf = []
            s.send(b'filler')
            while not exit_set.is_set():
                read_msg_from_socket(s, msg_buf)

        server = UDSStubServer(self.socket_path, on_bind=server_started.set, on_connect=on_connect)
        server.start()
        try:
            server_started.wait(2.0)
        except OSError as e:
            if e.errno == errno.ETIMEDOUT:
                self.fail('cannot start server')
        agent_status_cb = Mock(name='agent_status_cb')

        sdk = iottly.IottlySDK('testapp', self.socket_path,
                                on_agent_status_changed=agent_status_cb)
        sdk.start()

        client_connected.wait(2.0)
        time.sleep(2.0)
        sdk.stop()
        exit_set.set()
        server.stop()
        agent_status_cb.assert_has_calls([call('started'), call('stopped')])

    def test_receiving_stopping_signal_from_agent(self):
        server_started = multiprocessing.Event()
        client_connected = multiprocessing.Event()
        def on_connect(s):
            # Before sending the stopping signal we let fire
            # the started CB timeout.
            time.sleep(1.5)
            s.send(b'{"signal": {"agentstatus": "stopping"}}\n')
            client_connected.set()
        server = UDSStubServer(self.socket_path, on_bind=server_started.set, on_connect=on_connect)
        server.start()
        try:
            server_started.wait(2.0)
        except OSError as e:
            if e.errno == errno.ETIMEDOUT:
                self.fail('cannot start server')
        agent_status_cb = Mock(name='agent_status_cb')

        sdk = iottly.IottlySDK('testapp', self.socket_path,
                                on_agent_status_changed=agent_status_cb)
        sdk.start()
        client_connected.wait(2.0)
        time.sleep(3.0)  # give some time > timeout for deferred callback

        server.stop()
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
        except OSError as e:
            if e.errno == errno.ETIMEDOUT:
                self.fail('cannot start server')
        conn_status_cb = Mock(name='conn_status_cb')

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
        except OSError as e:
            if e.errno == errno.ETIMEDOUT:
                self.fail('Server doesn\'t received any connection')
        finally:
            sdk.stop()
            server.stop()

    def test_sending_msg_to_agent_with_channel(self):
        cb_called = multiprocessing.Event()
        def read_msg(s):
            msg_buf = []
            _ = read_msg_from_socket(s,msg_buf) # 1st msg in signal
            msg = read_msg_from_socket(s,msg_buf)
            expected_msg = '{"data": {"sdkclient": {"name": "testapp"}, "payload": {"test_metric": "test data"}, "channel": "test"}}'
            self.assertEqual(expected_msg, msg.decode())
            cb_called.set()
        server = UDSStubServer(self.socket_path, on_connect=read_msg)
        server.start()
        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.start()
        time.sleep(0.7)
        sdk.send({'test_metric': 'test data'}, channel='test')
        try:
            cb_called.wait(1.0)
            self.assertTrue(cb_called.is_set())
        except OSError as e:
            if e.errno == errno.ETIMEDOUT:
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
        except OSError as e:
            if e.errno == errno.ETIMEDOUT:
                self.fail('cannot start server')
        cmd_cb = Mock(name='cmd_cb')

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
        except OSError as e:
            if e.errno == errno.ETIMEDOUT:
                self.fail('cannot start server')
        cmd_cb = Mock(name='cmd_cb')

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
        except OSError as e:
            if e.errno == errno.ETIMEDOUT:
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

    def test_call_agent_with_disconnected_sdk_and_unknown_version(self):
        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.start()

        with self.assertRaises(InvalidAgentVersion):
            sdk.call_agent('echo')

    def test_call_agent_with_disconnected_sdk(self):
        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.start()
        sdk._agent_version = '1.8.6'

        with self.assertRaises(DisconnectedSDK):
            sdk.call_agent('echo')

    def test_call_agent(self):
        cb_called = multiprocessing.Event()
        def read_msg(s):
            msg_buf = []
            _ = read_msg_from_socket(s,msg_buf) # 1st msg in signal
            msg = read_msg_from_socket(s,msg_buf)
            self.assertEqual('{"signal": {"sdkclient": {"name": "testapp", "call": {"user_cmd": {"arg1": "foo"}}}}}', msg.decode())
            cb_called.set()
        server = UDSStubServer(self.socket_path, on_connect=read_msg)
        server.start()

        sdk = iottly.IottlySDK('testapp', self.socket_path)
        sdk.start()
        sdk._agent_version = '1.8.0'

        # This sleep guarantee that the call_agent sends data through the socket
        # after the initial version hand-shake. This is not required at runtime
        # because `call_agent` required the agent version to be set.
        time.sleep(0.5)
        sdk.call_agent('user_cmd', {'arg1': 'foo'})
        sdk.send({'test': 'foo'})

        if not cb_called.wait(1.0):
            server.stop()
            self.fail('Server doesn\'t received any connection')

        sdk.stop()
        server.stop()

    def test_call_agent_inside_connection_callback(self):
        """Test issue #5 https://github.com/tomorrowdata/iottly-sdk-python/issues/5
        """
        server_started = multiprocessing.Event()
        server_accepted_conn = multiprocessing.Event()
        server_init_rcvd = multiprocessing.Event()
        server_init_sent = multiprocessing.Event()
        server_call_agent_rcvd = multiprocessing.Event()

        sdk_on_agent_status_changed_called = multiprocessing.Event()
        sdk_call_agent_sent = multiprocessing.Event()

        def server_script(s):
            server_accepted_conn.set()
            msg_buf = []
            msg = read_msg_from_socket(s,msg_buf)
            exp_msg = '{"signal": {"sdkclient": {"name": "testapp", "status": "connected", "version": "%s"}}}' % iottly.__version__
            self.assertEqual(exp_msg, msg.decode())
            server_init_rcvd.set()
            s.send(b'{"signal": {"sdkinit": {"version": "1.8.0"}}}\n')
            server_init_sent.set()
            self.wait_or_fail(sdk_call_agent_sent, msg='call_agent was not invoked')
            call_agent_msg = read_msg_from_socket(s, msg_buf)
            self.assertEqual(b'{"signal": {"sdkclient": {"name": "testapp", "call": {"test_cmd": {}}}}}', call_agent_msg)
            server_call_agent_rcvd.set()
            s.close()

        def agent_status_cb(status):
            sdk_on_agent_status_changed_called.set()
            if status == 'started':
                sdk.call_agent('test_cmd', {})
                sdk_call_agent_sent.set()

        server = UDSStubServer(self.socket_path,
                            on_bind=server_started.set, on_connect=server_script)
        server.start()
        self.wait_or_fail(server_started, msg='Cannot start server')

        sdk = iottly.IottlySDK('testapp', self.socket_path,
                                on_agent_status_changed=agent_status_cb)
        sdk.start()
        self.wait_or_fail(server_accepted_conn, msg='Client did not connect')
        self.wait_or_fail(server_init_rcvd)
        self.wait_or_fail(server_init_sent)
        self.wait_or_fail(sdk_on_agent_status_changed_called, msg='Agent status changed CB not invoked')
        self.wait_or_fail(sdk_call_agent_sent, msg='call_agent was not invoked')
        self.wait_or_fail(server_call_agent_rcvd, msg='call_agent was not received')
        server.stop()
        sdk.stop()
