# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

import logging

from httpetcd import exceptions as etcd_exc

from loopster.services import softirq


LOG = logging.getLogger(__name__)
logging.warning("Module loopster.services.softirq_etcd is deprecated.")


class EtcdSingleSoftIrqService(softirq.SoftIrqService):
    """First attempt at etcd-backed locking implementation

    This class is deprecated, all of it's logic and more is implemented
    in SoftIrqService

    """

    def __init__(self, etcd_client, lock_key, lock_ttl,
                 step_period=1, loop_period=0.1, sender=None,
                 event_type=None, error_event_type=None):
        super(EtcdSingleSoftIrqService, self).__init__(
            step_period=step_period,
            loop_period=loop_period,
            sender=sender,
            event_type=event_type,
            error_event_type=error_event_type,
        )
        self._etcd = etcd_client
        self._lock = None
        self._lock_key = lock_key
        self._lock_ttl = lock_ttl

    def _wrapped_step(self, step_info):
        step_info["etcd_step_locked"] = False
        if self._lock is not None:
            try:
                self._lock.refresh()
            except etcd_exc.KVLockExpired as e:
                self._lock = None
                self._l(LOG).warning("Failed to refresh lock <%s>: %r",
                                     self._lock_key, e)

        if self._lock is None:
            try:
                self._lock = self._etcd.kvlock.acquire(key_name=self._lock_key,
                                                       ttl=self._lock_ttl)

                self._l(LOG).info("Successfully acquired lock <%s> for %s",
                                  self._lock_key, self._lock_ttl)
            except etcd_exc.KVLockAlreadyOccupied as e:
                self._l(LOG).debug("Failed to acquire lock <%s>: %r",
                                   self._lock_key, e)

        step_info["etcd_step_locked"] = self._lock is not None
        if self._lock is None:
            self._l(LOG).debug("Skipped step: lock is not taken")
            return

        return super(EtcdSingleSoftIrqService, self)._wrapped_step(step_info)

    def _teardown(self):
        if self._lock is not None:
            try:
                self._l(LOG).debug("Releasing lock <%s>...", self._lock_key)
                self._lock.release()
                self._l(LOG).info("Successfully released lock <%s>",
                                  self._lock_key)
            except Exception as e:
                self._l(LOG).warning("Failed to release lock <%s>: %r",
                                     self._lock_key, e)
        super(EtcdSingleSoftIrqService, self)._teardown()
