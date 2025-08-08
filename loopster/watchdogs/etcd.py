#    Copyright 2011 OpenStack Foundation
#    Copyright 2019-2021 Mail.ru Group.
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

import ctypes
import logging
import multiprocessing
import socket
import sys

from httpetcd.clients import wrapped_client as etcd
from httpetcd import exceptions as etcd_exc
import six

from loopster.watchdogs.base import WatchDog
from loopster.watchdogs import exceptions as wd_exc


_LEASE_DEFINED_INDEX = 0
_LEASE_ID_INDEX = 1

LOG = logging.getLogger(__name__)


class WatchdogMinorEtcdLockException(wd_exc.WatchDogMinorException):
    msg_template = "Watchdog minor etcd lock error: %(reason)r"


class WatchdogCriticalEtcdLockException(wd_exc.WatchDogCriticalException):
    msg_template = "Watchdog critical etcd lock error: %(reason)r"


class WatchdogHeartbeatCriticalException(wd_exc.WatchDogCriticalException):
    msg_template = "Watchdog heartbeat etcd lock error: %(reason)r"


def _wlm(msg, lock):
    prefix = "[lock:%s:%s] " % (lock.key, lock.id)
    return prefix + msg


class WatchDogEtcd(WatchDog):

    """Etcd-lock-based watchdog (with timer)

    Handles Etcd lock as a service workload guard.
    It's based on timer watchdog, so both mechanics work together.
    """

    def __init__(self, heartbeat_timeout, etcd_config, lock_key,
                 lock_label=None, lock_ttl=None, unsafe_lock_ttl=False):
        super(WatchDogEtcd, self).__init__(heartbeat_timeout)
        self._etcd_config = etcd_config
        self._etcd = etcd.WrappedHTTPEtcdClient(conf=etcd_config)
        self._lease_arr = multiprocessing.Array(ctypes.c_longlong, 2)
        self._lock_obj = None
        self._lock_key = lock_key
        self._lock_label = lock_label or socket.gethostname().split(".")[0]
        expected_ttl = (1 + heartbeat_timeout + etcd_config.timeout) * 3
        ttl = lock_ttl or expected_ttl
        if (not unsafe_lock_ttl) and (ttl < expected_ttl):
            raise ValueError("Unsafe lock TTL: %d < %d" % (ttl, expected_ttl))
        self._lock_ttl = ttl

    @property
    def _lock(self):
        return self._lock_obj

    @_lock.setter
    def _lock(self, value):
        self._lock_obj = value
        with self._lease_arr.get_lock():
            self._lease_arr[_LEASE_DEFINED_INDEX] = 0 if value is None else 1
            self._lease_arr[_LEASE_ID_INDEX] = getattr(value, "id", 0)

    def _refresh_lock(self):
        try:
            self._l(LOG).debug(_wlm("Refreshing lock...", self._lock))
            self._lock.refresh()
            self._l(LOG).debug(_wlm("Refreshed lock.", self._lock))
        except etcd_exc.KVLockExpired as e:
            self._l(LOG).info(_wlm("Lock has expired: %r", self._lock), e)
            self._lock = None
            raise

    def _get_lock_lease_id(self):
        with self._lease_arr.get_lock():
            if self._lease_arr[_LEASE_DEFINED_INDEX]:
                return self._lease_arr[_LEASE_ID_INDEX]

        raise WatchdogCriticalEtcdLockException(
            reason="[lock:%s] Lock is undefined" % self._lock_key)

    def _check_health(self):
        super(WatchDogEtcd, self)._check_health()

        if not self._in_context:
            return

        lease = self._etcd.lease.get(self._get_lock_lease_id())
        try:
            lock = self._etcd.kvlock.from_lease(lease)
        except etcd_exc.LeaseExpired:
            raise WatchdogCriticalEtcdLockException(
                reason="[lock:%s] Lock has expired" % self._lock_key
            )
        except Exception:
            t, v, tb = sys.exc_info()

            reason = "[lock:%s] Failed to get lock status: %r" % (
                self._lock_key,
                v,
            )
            error = WatchdogCriticalEtcdLockException(reason=reason)
            six.reraise(type(error), error, tb)
        else:
            # NOTE(rnebaluev) Unlock must
            #   only run if the process is completed.
            lock.refresh()

    def _on_enter(self):
        super(WatchDogEtcd, self)._on_enter()
        action = "refresh"
        try:
            if self._lock is not None:
                try:
                    self._refresh_lock()
                    return
                except etcd_exc.KVLockExpired:
                    pass

            action = "acquire"
            self._lock = self._etcd.kvlock.acquire(key_name=self._lock_key,
                                                   ttl=self._lock_ttl,
                                                   label=self._lock_label)
            self._l(LOG).info(_wlm("Acquired lock with TTL=%s, label=%s",
                                   self._lock),
                              self._lock_ttl, self._lock_label)
        except Exception:
            t, v, tb = sys.exc_info()
            self._l(LOG).debug("[lock:%s] Failed to %s lock (label=%s): %r",
                               self._lock_key, action, self._lock_label, v)
            error = (
                WatchdogCriticalEtcdLockException(reason=v)
                if isinstance(v, etcd_exc.KVLockCreateError) else
                WatchdogMinorEtcdLockException(reason=v)
            )
            six.reraise(type(error), error, tb)

    def generate_heartbeat(self):
        """Generate watchdog heartbeat

        Update timer & Etcd lock.
        """

        super(WatchDogEtcd, self).generate_heartbeat()
        if self._lock is not None:
            lock = self._lock
            try:
                self._refresh_lock()
            except Exception:
                t, v, tb = sys.exc_info()
                self._l(LOG).warning(_wlm("Failed to refresh lock: %r", lock),
                                     v)
                if self._in_context:
                    error = WatchdogHeartbeatCriticalException(
                        reason=_wlm("Failed to refresh lock: %r" % v, lock))
                    six.reraise(type(error), error, tb)
        elif self._in_context:
            msg = "[lock:%s] Lock is undefined within context" % self._lock_key
            raise WatchdogCriticalEtcdLockException(reason=msg)

    def teardown(self):
        """Gracefully teardown watchdog

        If lock is defined it will requested for release from Etcd cluster
        (any errors are ignored).
        """

        super(WatchDogEtcd, self).teardown()
        if self._lock is not None:
            try:
                self._l(LOG).debug(_wlm("Releasing lock...", self._lock))
                self._lock.release()
                self._l(LOG).info(_wlm("Successfully released lock",
                                  self._lock))
            except Exception as e:
                self._l(LOG).warning(
                    _wlm("Failed to release lock: %r", self._lock), e)
