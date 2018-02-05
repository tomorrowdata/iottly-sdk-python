import unittest

from iottly_sdk.iottly import IottlySDK

class TestIottlySDKApiArgTypes(unittest.TestCase):

    def test_send_args(self):
        sdk = IottlySDK('test app')

        with self.assertRaises(TypeError):
            sdk.send("test data")

        with self.assertRaises(ValueError):
            sdk.send({"test": set()})

    def test_subscribe_args(self):
        sdk = IottlySDK('test app')

        with self.assertRaises(TypeError):
            sdk.subscribe("cmd1", [])

        with self.assertRaises(TypeError):
            sdk.subscribe([], lambda x: x)
