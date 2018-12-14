import unittest
import json
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

from iottly_sdk.iottly import IottlySDK


class TestIottlySDKApiArgTypes(unittest.TestCase):

    def test_send_args(self):
        sdk = IottlySDK('test app')

        with self.assertRaises(TypeError):
            sdk.send("test data")

        with self.assertRaises(ValueError):
            sdk.send({"test": set()})

    def test_send_to_channel_args(self):
        sdk = IottlySDK('test app')

        with self.assertRaises(TypeError):
            sdk.send({"test": "foobar"}, channel=1234)

    def test_subscribe_args(self):
        sdk = IottlySDK('test app')

        with self.assertRaises(TypeError):
            sdk.subscribe("cmd1", [])

        with self.assertRaises(TypeError):
            sdk.subscribe([], lambda x: x)

    def test_call_agent_args(self):
        sdk = IottlySDK('test app')
        sdk._agent_version = '1.8.0'
        sdk._agent_linked = True

        with self.assertRaises(TypeError):
            sdk.call_agent("cmd1", "foo bar")

        with self.assertRaises(TypeError):
            sdk.call_agent([], {"cmd": {}})

    def test_call_agent_cmd_with_no_args(self):
        sdk = IottlySDK('test app')
        sdk._agent_version = '1.8.0'
        sdk._agent_linked = True
        m = Mock(name='_send_msg_through_socket', return_value=None)
        sdk._send_msg_through_socket = m

        sdk.call_agent('cmd1')
        self.assertTrue(m.called)
        exp = {'cmd1': {}}
        arg = m.call_args[0][0]
        res = json.loads(arg.decode())
        self.assertEqual(exp, res['signal']['sdkclient']['call'])


    def test_call_agent_cmd_with_args(self):
        sdk = IottlySDK('test app')
        sdk._agent_version = '1.8.0'
        sdk._agent_linked = True
        m = Mock(name='_send_msg_through_socket', return_value=None)
        sdk._send_msg_through_socket = m

        sdk.call_agent('cmd1', {'arg1': True, 'arg2': 'foobar'})
        self.assertTrue(m.called)
        exp = {'cmd1': {'arg1': True, 'arg2': 'foobar'}}
        arg = m.call_args[0][0]
        res = json.loads(arg.decode())
        self.assertEqual(exp, res['signal']['sdkclient']['call'])
