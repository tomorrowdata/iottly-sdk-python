import unittest
try:
    from unittest.mock import Mock, call
except ImportError:
    from mock.mock import Mock, call

from iottly_sdk.iottly import _read_msg_from_socket

class TestSocketMessageReceive(unittest.TestCase):

    def test_receive_data(self):
        data = [b'fixture data\n']
        socket = Mock()
        socket.recv = Mock(side_effect=data)

        msg_buf = []
        msgs = _read_msg_from_socket(socket, msg_buf)

        self.assertEqual(1, len(msgs))
        self.assertEqual('fixture data', msgs[0])

    def test_receive_data_with_more_messages(self):
        data = b'fixture data\nother fixture data\nand some more\n'
        socket = Mock()
        socket.recv = Mock(return_value=data)

        msg_buf = []
        msgs = _read_msg_from_socket(socket, msg_buf)

        self.assertEqual(3, len(msgs))
        self.assertEqual('fixture data', msgs[0])
        self.assertEqual('other fixture data', msgs[1])
        self.assertEqual('and some more', msgs[2])

    def test_receive_chuncked_messages(self):
        data = [b'fixture data\nother fixt', b'ure data\nand some more\n']
        socket = Mock()
        socket.recv = Mock(side_effect=data)

        msg_buf = []
        msgs = _read_msg_from_socket(socket, msg_buf)
        self.assertEqual(1, len(msgs))
        self.assertEqual('fixture data', msgs[0])

        msgs = _read_msg_from_socket(socket, msg_buf)
        self.assertEqual(2, len(msgs))
        self.assertEqual('other fixture data', msgs[0])
        self.assertEqual('and some more', msgs[1])


    def test_handle_socket_error(self):
        socket = Mock()
        socket.recv = Mock(side_effect=OSError())

        msg_buf = []
        msg = _read_msg_from_socket(socket, msg_buf)
        self.assertIsNone(msg)

    def test_draining_socket_data(self):
        data = [b'fixture data\n', b'']
        socket = Mock()
        socket.recv = Mock(side_effect=data)

        msg_buf = []
        msgs = _read_msg_from_socket(socket, msg_buf)
        self.assertEqual('fixture data', msgs[0])

        msg = _read_msg_from_socket(socket, msg_buf)
        self.assertIsNone(msg)
