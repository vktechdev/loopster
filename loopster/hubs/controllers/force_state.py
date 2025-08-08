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

import six

from loopster.hubs.controllers import base


LOG = logging.getLogger(__name__)


class AlwaysForceTargetStateController(base.AbstractController):

    """Simple controller that just set states in a loop."""

    def __init__(self):
        super(AlwaysForceTargetStateController, self).__init__()
        self._stop = False

    def manage(self, hub, driver):
        """Get states and decide what to do with services"""
        target_states = hub.get_target_states()
        current_states = driver.get_states()
        for unit_uuid, target_state in six.iteritems(target_states):
            if self._stop:
                self._l(LOG).info("Aborting state management...")
                return
            driver.set_state(
                unit_uuid, current_states[unit_uuid], target_state)

    def stop(self, driver):
        """Stop managing"""
        self._l(LOG).info("Stopping...")
        self._stop = True
