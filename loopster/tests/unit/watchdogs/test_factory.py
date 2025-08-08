# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2021 Mail.ru Group
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
import unittest

import mock

from loopster.watchdogs import base as wd_base
from loopster.watchdogs import etcd as wd_etcd
from loopster.watchdogs import exceptions
from loopster.watchdogs import factory


class WatchdogFactoryTestCase(unittest.TestCase):

    def test_create_dummy_watchdog(self):
        res = factory.get_watchdog(watchdog_type=factory.DUMMY_TYPE)
        self.assertIsInstance(res, wd_base.WatchDogBase)

    def test_create_timed_watchdog(self):
        res = factory.get_watchdog(
            watchdog_type=factory.TIMED_TYPE,
            heartbeat_timeout=789,
        )
        self.assertIsInstance(res, wd_base.WatchDog)

    def test_create_etcd_watchdog(self):
        fake_config = mock.Mock()
        fake_config.endpoints = ['a', 'b']
        fake_config.timeout = 99

        res = factory.get_watchdog(
            watchdog_type=factory.ETCD_TYPE,
            heartbeat_timeout=99,
            etcd_config=fake_config,
            lock_key='test key',
            lock_ttl=999,
            unsafe_lock_ttl=False,
        )
        self.assertIsInstance(res, wd_etcd.WatchDogEtcd)

    def test_create_unknown_watchdog(self):
        self.assertRaises(
            exceptions.WatchDogCriticalException,
            factory.get_watchdog,
            'unknown type'
        )

    def test_create_etcd_config(self):
        endpoints = ["http://example.com:2379"]
        namespace = 'loopster'
        timeout = 77
        res = factory.create_etcd_config(
            endpoints=endpoints,
            namespace=namespace,
            timeout=timeout,
        )

        self.assertEqual(endpoints, res.endpoints)
        self.assertEqual(namespace, res.namespace)
        self.assertEqual(timeout, res.timeout)
