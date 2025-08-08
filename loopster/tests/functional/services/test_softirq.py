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

import os
import time
import unittest
import uuid

from loopster import exceptions
from loopster.hubs.drivers import process
from loopster.services import softirq
from loopster import states
from loopster.watchdogs import base


class MonitoredSoftIrqService(softirq.SoftIrqService):
    def _step(self):
        time.sleep(1)


class SoftIrqServiceTestCase(unittest.TestCase):
    watchdog = base.WatchDog(heartbeat_timeout=10)

    def setUp(self):
        self.service_uuid = uuid.uuid4()
        self.driver = process.ProcessDriver()
        self.driver.add_service(self.service_uuid, MonitoredSoftIrqService,
                                {
                                    'watchdog': self.watchdog,
                                })
        self.svc_storage = self.driver._services[self.service_uuid]

    def stop_process(self):
        self.driver.set_state(
            self.service_uuid,
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage),
            states.State.STOPPED)
        self.driver._wait_service(self.service_uuid, self.svc_storage)
        self.assertEqual(
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage),
            states.State.STOPPED)

    def test_initial_state(self):
        self.assertEqual(
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage),
            states.State.INITIAL)

        self.stop_process()

    def test_initial_to_running(self):
        self.driver.set_state(
            self.service_uuid, states.State.INITIAL, states.State.RUNNING)

        self.assertEqual(
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage),
            states.State.RUNNING)
        self.stop_process()

    def test_same_states(self):
        self.driver.set_state(
            self.service_uuid, states.State.INITIAL, states.State.RUNNING)

        self.driver.set_state(
            self.service_uuid, states.State.RUNNING, states.State.RUNNING)

        self.assertEqual(
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage),
            states.State.RUNNING)

        self.stop_process()

    def test_usual_stop(self):
        self.driver.set_state(
            self.service_uuid, states.State.INITIAL, states.State.RUNNING)

        self.driver.set_state(

            self.service_uuid, states.State.RUNNING, states.State.STOPPED)
        self.driver._wait_service(self.service_uuid, self.svc_storage)

        self.assertEqual(
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage),
            states.State.STOPPED)
        self.assertEqual(
            self.driver._services[self.service_uuid]['process'].exitcode, -15)

    def test_restart_after_stop(self):
        self.driver.set_state(
            self.service_uuid, states.State.INITIAL, states.State.RUNNING)
        self.driver.set_state(
            self.service_uuid, states.State.RUNNING, states.State.STOPPED)
        self.driver._wait_service(self.service_uuid, self.svc_storage)

        self.driver.set_state(
            self.service_uuid, states.State.STOPPED, states.State.RUNNING)

        self.assertEqual(
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage),
            states.State.RUNNING)

        self.stop_process()

    def test_kill(self):
        self.driver.set_state(
            self.service_uuid, states.State.INITIAL, states.State.RUNNING)

        pid = self.driver._services[self.service_uuid]['process'].pid
        os.kill(pid, 9)
        self.driver._wait_service(self.service_uuid, self.svc_storage)

        self.assertEqual(
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage),
            states.State.FAILED)

    def test_restart_after_killed(self):
        self.driver.set_state(
            self.service_uuid, states.State.INITIAL, states.State.RUNNING)
        pid = self.driver._services[self.service_uuid]['process'].pid
        os.kill(pid, 9)
        self.driver._wait_service(self.service_uuid, self.svc_storage)

        self.driver.set_state(
            self.service_uuid, states.State.FAILED, states.State.RUNNING)

        self.assertEqual(
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage),
            states.State.RUNNING)

        self.stop_process()

    def test_wrong_set_state(self):
        self.driver.set_state(
            self.service_uuid, states.State.INITIAL, states.State.RUNNING)

        self.assertRaises(exceptions.DriverUnsupportedState,
                          self.driver.set_state, self.service_uuid,
                          states.State.RUNNING, states.State.INITIAL)

        self.stop_process()

    def test_stale_heartbeat(self):
        wd = self.svc_storage[process.SERVICE_KEY].get_watchdog()
        wd._heartbeat_timeout = 0
        self.driver.set_state(
            self.service_uuid, states.State.INITIAL, states.State.RUNNING)
        self.assertEqual(
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage
            ),
            states.State.NUMB
        )
        self.driver.set_state(
            self.service_uuid,
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage
            ),
            states.State.STOPPED
        )
        self.watchdog._heartbeat_timeout = 1

    def test_heartbeat(self):
        self.driver.set_state(
            self.service_uuid, states.State.INITIAL, states.State.RUNNING)
        self.assertEqual(
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage
            ),
            states.State.RUNNING
        )
        self.assertEqual(
            self.driver._get_service_state(
                self.service_uuid, self.svc_storage
            ),
            states.State.RUNNING
        )
        self.stop_process()
