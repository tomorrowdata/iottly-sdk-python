# Copyright 2018 TomorrowData Srl
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import six
from distutils.version import StrictVersion


# ======================================================================== #
# ============================ Decorators ================================ #
# ======================================================================== #
def min_agent_version(min_version):
    """Ensures SDK/agent compatibility for method invocations in the IottlySDK.

    This decorator checks the agent version stored in `self._agent_version`
    against the one provided as  argument; if the current version is >= than
    the required version the decorated method is executed else an `InvalidAgentVersion`
    error is raised.
    """
    def decorator(f):
        min_required_version = StrictVersion(min_version)
        @six.wraps(f)
        def wrapper(self, *args, **kwargs):
            if not self._agent_version:
                err_msg = ''
                'Method "{}" requires iottly'
                ' agent >= {} but no version was provided.'
                'Probably the SDK is connected to an agent < 1.8.0'.format(
                                  f.__name__, min_version)
                raise InvalidAgentVersion(err_msg)
            else:
                current_version = StrictVersion(self._agent_version)
                if current_version >= min_required_version:
                    return f(self, *args, **kwargs)
                else:
                    err_msg = ''
                    'Method "{}" requires iottly'
                    ' agent >= {} but version {} is'
                    ' currently running.'.format(
                                      f.__name__, min_version, current_version)
                    raise InvalidAgentVersion(err_msg)
        return wrapper
    return decorator

# ======================================================================== #
# ============================= Exceptions =============================== #
# ======================================================================== #

class InvalidAgentVersion(Exception): pass
