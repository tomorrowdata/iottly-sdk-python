import unittest
from iottly_sdk.utils import min_agent_version
from iottly_sdk.errors import InvalidAgentVersion

class TestVersionCheckDecorator(unittest.TestCase):

    def setUp(self):
        pass

    def test_invalid_version_check_when_no_version_available(self):
        class SDKStubClass:
            def __init__(self):
                self._agent_version = None
            @min_agent_version('1.0.0')
            def testMethod(self):
                return True
        sdk = SDKStubClass()

        with self.assertRaises(InvalidAgentVersion) as e:
            sdk.testMethod()

    def test_invalid_version_check_whit_older_version(self):
        class SDKStubClass:
            def __init__(self):
                self._agent_version = '0.9.5'

            @min_agent_version('1.0.0')
            def testMethod(self):
                return True
        sdk = SDKStubClass()

        with self.assertRaises(InvalidAgentVersion) as e:
            sdk.testMethod()

    def test_invalid_version_check_whit_right_version(self):
        class SDKStubClass:
            def __init__(self):
                self._agent_version = '1.0.0'

            @min_agent_version('1.0.0')
            def testMethod(self):
                return True
        sdk = SDKStubClass()

        res = sdk.testMethod()

        self.assertTrue(res)

    def test_invalid_version_check_whit_newer_version(self):
        class SDKStubClass:
            def __init__(self):
                self._agent_version = '1.2.4'

            @min_agent_version('1.0.0')
            def testMethod(self):
                return True
        sdk = SDKStubClass()

        res = sdk.testMethod()

        self.assertTrue(res)
