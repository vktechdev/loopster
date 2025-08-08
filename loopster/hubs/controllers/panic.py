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

import logging

from loopster.common import exc
import six

from loopster import exceptions
from loopster.hubs.controllers import base
from loopster import states


LOG = logging.getLogger(__name__)


class PanicController(base.AbstractController):
    """Simple controller that stops on any problem."""

    __default_panic_states__ = {states.State.FAILED, states.State.NUMB}

    def __init__(self, panic_states=None):
        super(PanicController, self).__init__()
        self._panic_states = (panic_states
                              or self.__default_panic_states__.copy())
        self._stop = False

    def _fast_stop(self, driver, current_states):
        self._l(LOG).info("Stopping all services...")
        for u, c in six.iteritems(current_states):
            with exc.suppress_any():
                driver.set_state(u, c, states.State.STOPPED)

    def manage(self, hub, driver):
        """Get states and decide what to do with services"""
        target_states = hub.get_target_states()
        current_states = driver.get_states()
        for unit_uuid, target_state in six.iteritems(target_states):
            if self._stop:
                self._l(LOG).info("Aborting state management...")
                return
            current_state = current_states[unit_uuid]
            if current_state in self._panic_states:
                reason = ("Unit %s has reached unexpected state=%r"
                          % (unit_uuid, current_state))
                self._l(LOG).error(reason)
                self._fast_stop(driver, current_states)
                raise exceptions.StopHub(reason=reason)
            else:
                driver.set_state(
                    unit_uuid, current_state, target_state)

    def stop(self, driver):
        """Stop managing"""
        self._l(LOG).info("Stopping...")
        self._stop = True
