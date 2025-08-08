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

import logging
import time
import unittest
import uuid

import mock
import six

from loopster import exceptions
from loopster.hubs.drivers import process
from loopster.services import softirq
from loopster import states

LOG = logging.getLogger(__name__)


class BasicService(softirq.SoftIrqService):
    def _step(self):
        time.sleep(10)


class ProcessDriverTestCase(unittest.TestCase):
    def setUp(self):
        self.service_uuid = uuid.uuid4()
        self.driver = process.ProcessDriver()

    def test_validate_target_state(self):
        self.assertIsNone(
            self.driver.validate_target_state(states.State.STOPPED))

    def test_validate_target_state_negative(self):
        self.assertRaises(
            exceptions.DriverUnsupportedState,
            self.driver.validate_target_state, states.State.INITIAL)

    def test_set_state_same(self):
        self.assertIsNone(self.driver.set_state(None, states.State.STOPPED,
                                                states.State.STOPPED))

    def test_add_service_exists(self):
        self.driver.add_service(self.service_uuid, BasicService, {})

        self.assertRaises(exceptions.ServiceExists,
                          self.driver.add_service,
                          self.service_uuid,
                          BasicService,
                          {})

    def test_get_process_state_initial(self):
        process = mock.MagicMock()
        process.pid = None

        self.assertEqual(self.driver._get_process_state(process),
                         states.State.INITIAL)

    def test_get_process_state_running(self):
        process = mock.MagicMock()
        process.exitcode = None

        self.assertEqual(self.driver._get_process_state(process),
                         states.State.RUNNING)

    def test_get_process_state_stopped(self):
        process = mock.MagicMock()
        process.exitcode = 0

        self.assertEqual(self.driver._get_process_state(process),
                         states.State.STOPPED)

    def test_get_process_state_failed(self):
        process = mock.MagicMock()

        self.assertEqual(self.driver._get_process_state(process),
                         states.State.FAILED)

    def test_get_service_state(self):
        svc_storage = {'svc_class': BasicService, 'svc_kwargs': {}}
        self.driver._init_service(None, svc_storage)

        self.assertEqual(self.driver._get_service_state(None, svc_storage),
                         states.State.INITIAL)

    def test_get_service_state_stopped_flag(self):
        svc_storage = {'svc_class': BasicService, 'svc_kwargs': {}}
        self.driver._init_service(None, svc_storage)
        self.driver._set_stopped_state_handler(None, None, None, svc_storage)

        self.assertEqual(self.driver._get_service_state(None, svc_storage),
                         states.State.STOPPED)

    def test_get_service_state_running_stopped_flag(self):
        svc_storage = {'svc_class': BasicService, 'svc_kwargs': {}}
        self.driver._init_service(None, svc_storage)
        self.driver._set_stopped_state_handler(None, None, None, svc_storage)

        svc_storage['process'] = mock.MagicMock()
        svc_storage['process'].exitcode = None

        self.assertEqual(self.driver._get_service_state(None, svc_storage),
                         states.State.RUNNING)

    @mock.patch('loopster.hubs.drivers.process.ProcessDriver._get_service')
    def test_override_service_state(self, get_service):
        fake_watchdog = mock.Mock(name="fake_watchdog")
        fake_service = mock.Mock(name="fake_service")
        fake_service.get_watchdog.return_value = fake_watchdog
        get_service.return_value = fake_service
        case_map = {(s, force, wd_alive): s
                    for s in states.State
                    for force in [True, False]
                    for wd_alive in [True, False]}
        overrides_numb = {
            (states.State.RUNNING, force, False): states.State.NUMB
            for force in [True, False]
        }
        overrides_forcibly = {
            (s, True, wd_alive): states.State.STOPPED
            for wd_alive in [True, False]
            for s in states.State
            if s is not states.State.RUNNING
        }
        # NOTE(d.burmistrov): ORDER MATTERS! :)
        case_map.update(overrides_numb)
        case_map.update(overrides_forcibly)

        for k, expected_state in six.iteritems(case_map):
            real_state, force, wd_alive = k
            LOG.info("For <%s\tforce=%s\twd_alive=%s>\texpecting\t<%s>",
                     real_state, force, wd_alive, expected_state)
            fake_watchdog.is_alive.return_value = wd_alive

            overriden_state = self.driver._override_service_state(
                target_uuid="fake",
                svc_storage={process.FORCIBLY_STOPPED_KEY: force},
                real_state=real_state,
            )

            self.assertIs(expected_state, overriden_state)
