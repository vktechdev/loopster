# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright 2020 Mail.ru Group.
#
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import abc

from loopster.common import obj
import six


@six.add_metaclass(abc.ABCMeta)
class AbstractController(obj.BaseObject):

    @abc.abstractmethod
    def manage(self, hub, driver):
        """Get states and decide what to do with services"""
        raise NotImplementedError()

    @abc.abstractmethod
    def stop(self, driver):
        """Stop managing"""
        # on signal handling: fast out of state managing
        raise NotImplementedError()
