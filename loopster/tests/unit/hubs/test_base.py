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

import time
import unittest
import uuid

import mock

from loopster import exceptions
from loopster.hubs import base
from loopster.services import softirq
from loopster import states
from loopster import units


class BasicService(softirq.SoftIrqService):
    def _step(self):
        time.sleep(10)


class BaseHubTestCase(unittest.TestCase):
    def setUp(self):
        self.service_uuid = uuid.uuid4()
        self.driver = mock.MagicMock()
        self.controller = mock.MagicMock()
        self.hub = base.BaseHub(driver=self.driver, controller=self.controller,
                                step_period=0, loop_period=0)

    def test_initial(self):
        self.assertEqual(self.hub.get_target_states(), {})

    def test_add_service(self):
        unit = self.hub.add_service(BasicService)

        self.assertEqual(self.hub.get_target_states(),
                         {unit.uuid: states.State.RUNNING})

    def test_add_unit(self):
        unit = units.Unit(BasicService, {}, states.State.RUNNING)
        self.hub.add_unit(unit)
        unit.state = states.State.STOPPED

        self.assertEqual(self.hub.get_target_states(),
                         {unit.uuid: states.State.RUNNING})

    def test_add_unit_invalid_state(self):
        unit = units.Unit(BasicService, {}, states.State.FAILED)
        self.driver.validate_target_state = mock.Mock(
            side_effect=exceptions.DriverUnsupportedState())

        self.assertRaises(
            exceptions.DriverUnsupportedState, self.hub.add_unit, unit)

    def test_add_unit_duplicate(self):
        unit = units.Unit(BasicService, {}, states.State.RUNNING)
        self.hub.add_unit(unit)

        self.assertRaises(exceptions.UnitExists, self.hub.add_unit, unit)

    def test_update_unit(self):
        unit = units.Unit(BasicService, {}, states.State.RUNNING)
        self.hub.add_unit(unit)

        self.assertEqual(self.hub.get_target_states(),
                         {unit.uuid: states.State.RUNNING})

        unit.state = states.State.STOPPED
        self.hub.update_unit(unit)

        self.assertEqual(self.hub.get_target_states(),
                         {unit.uuid: states.State.STOPPED})

    def test_update_unit_invalid_state(self):
        unit = units.Unit(BasicService, {}, states.State.FAILED)
        self.hub.add_unit(unit)
        self.driver.validate_target_state = mock.Mock(
            side_effect=exceptions.DriverUnsupportedState())

        self.assertRaises(
            exceptions.DriverUnsupportedState, self.hub.update_unit, unit)

    def test_remove_unit(self):
        unit = units.Unit(BasicService, {}, states.State.RUNNING)
        self.hub.add_unit(unit)

        self.assertEqual(self.hub.get_target_states(),
                         {unit.uuid: states.State.RUNNING})

        self.hub.remove_unit(unit)

        self.driver.remove_service.assert_called_once()
        self.assertEqual(self.hub.get_target_states(),
                         {})

    def test_remove_unit_nonexist(self):
        unit = units.Unit(BasicService, {}, states.State.RUNNING)
        self.hub.add_unit(unit)
        self.hub.remove_unit(unit)

        self.assertRaises(
            exceptions.UnitNotFound, self.hub.remove_unit, unit)

    def test_serve(self):
        self.hub.add_service(BasicService)
        # stop cycle by exception on second iteration
        self.controller.manage = mock.Mock(
            side_effect=[None, exceptions.StopHub(reason='Test reason')])
        self.hub.serve()

        self.assertEqual(self.controller.manage.call_count, 2)
        self.controller.stop.assert_called_once()
        self.driver.stop_all_services.assert_called_once()
        self.driver.wait_all_services.assert_called_once()

    def test_serve_stop_same_iteration(self):
        self.hub.add_service(BasicService)
        # stop cycle by exception on first iteration
        self.controller.manage = mock.Mock(
            side_effect=[exceptions.StopHub(reason='Test reason'), None])
        self.hub.serve()

        self.assertEqual(self.controller.manage.call_count, 1)
        self.controller.stop.assert_called_once()
        self.driver.stop_all_services.assert_called_once()
        self.driver.wait_all_services.assert_called_once()
