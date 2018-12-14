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

class InvalidAgentVersion(Exception):
    """Exception raised when calling an SDK method that requires
    a **iottly agent** version greater that the one of the agent
    currently connected.
    """
    pass


class DisconnectedSDK(Exception):
    """Exception raised when calling an SDK method that want to
    communicate in a non-blocking fashion with the **iottly agent**
    while the SDK is disconnected from the agent.
    """
    pass
