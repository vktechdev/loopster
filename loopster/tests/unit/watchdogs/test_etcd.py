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

import mock
import unittest

from httpetcd import exceptions as etcd_exc

from loopster.watchdogs import etcd


class GenerateHeartbeatTestCase(unittest.TestCase):

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.etcd.WatchDogEtcd._refresh_lock')
    @mock.patch('loopster.watchdogs.base.WatchDog.generate_heartbeat')
    def test_no_context_no_lock(self, supermethod, refresh, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')

        wd.generate_heartbeat()

        supermethod.assert_called_once()
        refresh.assert_not_called()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.etcd.WatchDogEtcd._refresh_lock')
    @mock.patch('loopster.watchdogs.base.WatchDog.generate_heartbeat')
    def test_with_context_no_lock(self, supermethod, refresh, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        wd._in_context = True

        self.assertRaises(etcd.WatchdogCriticalEtcdLockException,
                          wd.generate_heartbeat)

        supermethod.assert_called_once()
        refresh.assert_not_called()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.base.WatchDog.generate_heartbeat')
    def test_with_context_with_lock_refreshed(self, supermethod, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        wd._in_context = True
        fake_lock = mock.Mock()
        wd._lock_obj = fake_lock

        wd.generate_heartbeat()

        supermethod.assert_called_once()
        fake_lock.refresh.assert_called_once()

    @mock.patch('loopster.watchdogs.base.WatchDog.generate_heartbeat')
    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    def test_with_context_with_lock_not_refreshed(self, supermethod, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        wd._in_context = True
        fake_lock = mock.Mock()
        fake_lock.refresh.side_effect = ValueError()
        wd._lock_obj = fake_lock

        self.assertRaises(etcd.WatchdogHeartbeatCriticalException,
                          wd.generate_heartbeat)

        supermethod.assert_called_once()
        fake_lock.refresh.assert_called_once()

    @mock.patch('loopster.watchdogs.base.WatchDog.generate_heartbeat')
    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    def test_no_context_with_lock_not_refreshed(self, supermethod, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock()
        fake_lock.refresh.side_effect = ValueError()
        wd._lock_obj = fake_lock

        wd.generate_heartbeat()

        supermethod.assert_called_once()
        fake_lock.refresh.assert_called_once()


class TeardownTestCase(unittest.TestCase):

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.etcd._wlm')
    @mock.patch('loopster.watchdogs.base.WatchDog.teardown')
    def test_no_lock(self, supermethod, wlm, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')

        wd.teardown()

        supermethod.assert_called_once()
        wlm.assert_not_called()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.base.WatchDog.teardown')
    def test_lock_released(self, supermethod, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock()
        wd._lock_obj = fake_lock

        wd.teardown()

        supermethod.assert_called_once()
        fake_lock.release.assert_called_once()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.base.WatchDog.teardown')
    def test_not_released(self, supermethod, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock()
        fake_lock.refresh.side_effect = ValueError()
        wd._lock_obj = fake_lock

        wd.teardown()

        supermethod.assert_called_once()
        fake_lock.release.assert_called_once()


class RefreshTestCase(unittest.TestCase):

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    def test_success(self, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock()
        wd._lock_obj = fake_lock

        wd._refresh_lock()

        fake_lock.refresh.assert_called_once()
        self.assertIs(fake_lock, wd._lock_obj)

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    def test_expire(self, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock()
        fake_lock.refresh.side_effect = etcd_exc.KVLockExpired()
        wd._lock_obj = fake_lock

        self.assertRaises(etcd_exc.KVLockExpired, wd._refresh_lock)

        fake_lock.refresh.assert_called_once()
        self.assertIs(None, wd._lock)

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    def test_failure(self, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock()
        fake_lock.refresh.side_effect = ValueError()
        wd._lock_obj = fake_lock

        self.assertRaises(ValueError, wd._refresh_lock)

        fake_lock.refresh.assert_called_once()
        self.assertIs(fake_lock, wd._lock)


class OnEnterTestCase(unittest.TestCase):

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.etcd.WatchDogEtcd._refresh_lock')
    @mock.patch('loopster.watchdogs.base.WatchDog._on_enter')
    def test_no_lock_success(self, supermethod, refresh, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')

        wd._on_enter()

        supermethod.assert_called_once()
        refresh.assert_not_called()
        wd._etcd.kvlock.acquire.assert_called_once()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.etcd.WatchDogEtcd._refresh_lock')
    @mock.patch('loopster.watchdogs.base.WatchDog._on_enter')
    def test_no_lock_error(self, supermethod, refresh, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        wd._etcd.kvlock.acquire.side_effect = ValueError()

        self.assertRaises(etcd.WatchdogMinorEtcdLockException,
                          wd._on_enter)

        supermethod.assert_called_once()
        refresh.assert_not_called()
        wd._etcd.kvlock.acquire.assert_called_once()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.etcd.WatchDogEtcd._refresh_lock')
    @mock.patch('loopster.watchdogs.base.WatchDog._on_enter')
    def test_connect_error(self, supermethod, refresh, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        wd._etcd.kvlock.acquire.side_effect = etcd_exc.KVLockCreateError()

        self.assertRaises(etcd.WatchdogCriticalEtcdLockException,
                          wd._on_enter)

        supermethod.assert_called_once()
        refresh.assert_not_called()
        wd._etcd.kvlock.acquire.assert_called_once()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.etcd.WatchDogEtcd._refresh_lock')
    @mock.patch('loopster.watchdogs.base.WatchDog._on_enter')
    def test_with_lock_refresh_error(self, supermethod, refresh, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock()
        wd._lock_obj = fake_lock
        refresh.side_effect = ValueError()

        self.assertRaises(etcd.WatchdogMinorEtcdLockException,
                          wd._on_enter)

        supermethod.assert_called_once()
        refresh.assert_called_once()
        wd._etcd.kvlock.acquire.assert_not_called()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.etcd.WatchDogEtcd._refresh_lock')
    @mock.patch('loopster.watchdogs.base.WatchDog._on_enter')
    def test_with_lock_refresh_expired(self, supermethod, refresh, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock()
        wd._lock_obj = fake_lock
        refresh.side_effect = etcd_exc.KVLockExpired()

        wd._on_enter()

        supermethod.assert_called_once()
        refresh.assert_called_once()
        wd._etcd.kvlock.acquire.assert_called_once()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.etcd.WatchDogEtcd._refresh_lock')
    @mock.patch('loopster.watchdogs.base.WatchDog._on_enter')
    def test_with_lock_acquire_error(self, supermethod, refresh, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock()
        wd._lock_obj = fake_lock
        refresh.side_effect = etcd_exc.KVLockExpired()
        wd._etcd.kvlock.acquire.side_effect = etcd_exc.KVLockAlreadyOccupied()

        self.assertRaises(etcd.WatchdogMinorEtcdLockException,
                          wd._on_enter)

        supermethod.assert_called_once()
        refresh.assert_called_once()
        wd._etcd.kvlock.acquire.assert_called_once()


class LockSetterTestCase(unittest.TestCase):

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    def test_set_none(self, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')

        wd._lock = None

        with wd._lease_arr.get_lock():
            self.assertEqual(wd._lease_arr[0], 0)
            self.assertEqual(wd._lease_arr[1], 0)

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    def test_no_lock_success(self, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock(id=42)

        wd._lock = fake_lock

        with wd._lease_arr.get_lock():
            self.assertEqual(wd._lease_arr[0], 1)
            self.assertEqual(wd._lease_arr[1], 42)


class CheckHealthTestCase(unittest.TestCase):

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.base.WatchDog._check_health')
    def test_no_context(self, supermethod, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')

        with mock.patch.object(wd, '_lease_arr') as lease_arr:
            wd._check_health()

            supermethod.assert_called_once()
            lease_arr.get_lock.assert_not_called()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.base.WatchDog._check_health')
    def test_with_context_no_lock(self, supermethod, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        wd._in_context = True
        wd._lock = None

        self.assertRaises(etcd.WatchdogCriticalEtcdLockException,
                          wd._check_health)

        supermethod.assert_called_once()
        wd._etcd.lease.get.assert_not_called()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.base.WatchDog._check_health')
    def test_context_lock(self, supermethod, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock(id=42)

        wd._in_context = True

        wd._lock = fake_lock
        wd._etcd.kvlock.from_lease.return_value = mock.Mock()

        with mock.patch.object(wd, '_lease_arr') as lease_arr:
            wd._check_health()

            supermethod.assert_called_once()
            lease_arr.get_lock.assert_called_once()
            wd._etcd.kvlock.from_lease.assert_called_once()

    @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    @mock.patch('loopster.watchdogs.base.WatchDog._check_health')
    def test_context_lock_with_error(self, supermethod, wetcd):
        wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
                               etcd_config=mock.Mock(timeout=1),
                               lock_key='lock_key')
        fake_lock = mock.Mock(id=42)

        wd._in_context = True

        wd._lock = fake_lock
        wd._etcd.kvlock.from_lease.side_effect = (
            etcd.WatchdogHeartbeatCriticalException()
        )

        with mock.patch.object(wd, "_lease_arr") as lease_arr:
            with self.assertRaises(
                etcd.WatchdogCriticalEtcdLockException
            ) as err:
                wd._check_health()
            self.assertEqual(
                err.exception.message,
                "Watchdog critical etcd lock error: '[lock:lock_key] "
                "Failed to get lock status: loopster.watchdogs."
                "etcd.WatchdogHeartbeatCriticalException()'",
            )

            supermethod.assert_called_once()
            lease_arr.get_lock.assert_called_once()
            wd._etcd.kvlock.from_lease.assert_called_once()

    # @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    # @mock.patch('httpetcd.wrapped.managers.kvlock.WrappedKVLockManager.get')
    # @mock.patch('loopster.watchdogs.base.WatchDog._check_health')
    # def test_with_context_alive_lock(self, supermethod, get, wetcd):
    #     wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
    #                            etcd_config=mock.Mock(timeout=1),
    #                            lock_key='lock_key')
    #     fake_lock = mock.Mock(id=42)
    #     fake_lock.alive.return_value = True
    #     wd._in_context = True
    #     wd._lock = fake_lock
    #     get.return_value = fake_lock
    #
    #     wd._check_health()
    #
    #     supermethod.assert_called_once()
    #     fake_lock.alive.assert_called_once()
    #
    # @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    # @mock.patch('httpetcd.wrapped.managers.kvlock.WrappedKVLockManager.get')
    # @mock.patch('loopster.watchdogs.base.WatchDog._check_health')
    # def test_with_context_expired_lock(self, supermethod, get, wetcd):
    #     wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
    #                            etcd_config=mock.Mock(timeout=1),
    #                            lock_key='lock_key')
    #     fake_lock = mock.Mock(id=42)
    #     fake_lock.alive.return_value = False
    #     wd._in_context = True
    #     wd._lock = fake_lock
    #     get.return_value = fake_lock
    #
    #     self.assertRaises(etcd.WatchdogCriticalEtcdLockException,
    #                       wd._check_health)
    #
    #     supermethod.assert_called_once()
    #     fake_lock.alive.assert_called_once()
    #
    # @mock.patch('httpetcd.clients.wrapped_client.WrappedHTTPEtcdClient')
    # @mock.patch('httpetcd.wrapped.managers.kvlock.WrappedKVLockManager.get')
    # @mock.patch('loopster.watchdogs.base.WatchDog._check_health')
    # def test_with_context_lock_alive_error(self, supermethod, get, wetcd):
    #     wd = etcd.WatchDogEtcd(heartbeat_timeout=5,
    #                            etcd_config=mock.Mock(timeout=1),
    #                            lock_key='lock_key')
    #     fake_lock = mock.Mock(id=42)
    #     fake_lock.alive.side_effect = ValueError()
    #     wd._in_context = True
    #     wd._lock = fake_lock
    #     get.return_value = fake_lock
    #
    #     self.assertRaises(etcd.WatchdogCriticalEtcdLockException,
    #                       wd._check_health)
    #
    #     supermethod.assert_called_once()
    #     fake_lock.alive.assert_called_once()
