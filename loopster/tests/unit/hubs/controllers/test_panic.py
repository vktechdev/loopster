# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2020 Mail.ru Group
#
# All Rights Reserved.
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

import mock
import unittest

from loopster import exceptions
from loopster.hubs import base
from loopster.hubs.controllers import panic
from loopster import states
from loopster import units


class BasicService(object):
    pass


class RestartControllerTestCase(unittest.TestCase):
    def get_driver(self, units):
        driver = mock.Mock()
        driver.get_states.return_value = units
        return driver

    def test_success_manage(self):
        unit = units.Unit(BasicService, {}, states.State.RUNNING, '1')
        current_units = {
            '1': states.State.RUNNING}
        driver = self.get_driver(current_units)
        controller = panic.PanicController()
        hub = base.BaseHub(driver=driver, controller=controller)
        hub.add_unit(unit)

        controller.manage(hub, driver)

        driver.set_state.assert_called()

    def test_manage_raise(self):
        unit = units.Unit(BasicService, {}, states.State.RUNNING, '1')
        current_units = {
            '1': states.State.FAILED}
        driver = self.get_driver(current_units)
        controller = panic.PanicController()
        hub = base.BaseHub(driver=driver, controller=controller)
        hub.add_unit(unit)

        self.assertRaises(exceptions.StopHub,
                          controller.manage,
                          hub,
                          driver)

    def test_stop(self):
        unit = units.Unit(BasicService, {}, states.State.RUNNING, '1')
        current_units = {
            '1': states.State.RUNNING}
        driver = self.get_driver(current_units)
        controller = panic.PanicController()
        hub = base.BaseHub(driver=driver, controller=controller)
        hub.add_unit(unit)

        controller.manage(hub, driver)
        controller.stop(driver)
        controller.manage(hub, driver)

        driver.set_state.assert_called_once()
