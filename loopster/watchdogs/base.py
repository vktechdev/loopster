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
import time

from loopster.common import obj

from loopster.watchdogs import exceptions as exc


LOG = logging.getLogger(__name__)


class WatchDogBase(obj.BaseObject):

    """Base watchdog

    Fully functional watchdog but does nothing.
    Should be subclassed for real watchdog checks.
    """

    def __init__(self):
        super(WatchDogBase, self).__init__()
        self._failed = False
        self._in_context_local = False
        self._in_context_value = multiprocessing.Value("i", False)

    @property
    def _in_context(self):
        with self._in_context_value.get_lock():
            return self._in_context_value.value or self._in_context_local

    @_in_context.setter
    def _in_context(self, value):
        with self._in_context_value.get_lock():
            self._in_context_value.value = value

    def _on_enter(self):
        pass

    def __enter__(self):
        try:
            self._in_context_local = True
            # self._l(LOG).debug("Preparing context...")
            self._on_enter()
            # self._l(LOG).debug("Generating heartbeat...")
            self.generate_heartbeat()
            # self._l(LOG).debug("Checking final health status...")
            self._check_health()
            self._in_context = True
        finally:
            self._in_context_local = False

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._in_context = False

    def __copy__(self):
        # noinspection PyArgumentList
        return type(self)(**self._init_kwargs)

    def _check_health(self):
        if self._failed:
            raise exc.ServiceIsMarkedFailed()

    def is_alive(self):
        """Check if watchdog is alive (always returns boolean)"""

        try:
            self._check_health()
            self._l(LOG).debug("The service is alive.")
            return True
        except exc.WatchDogMinorException as e:
            self._l(LOG).info("The service is not alive due to %r", e)
        except Exception:
            self._l(LOG).exception("Unexpected error during health check:")
        return False

    def mark_failed(self):
        """Manually mark watchdog as failed"""

        self._failed = True
        self._l(LOG).info("Watchdog was manually marked as failed")

    def generate_heartbeat(self):
        """Generate watchdog heartbeat"""
        pass

    def teardown(self):
        """Gracefully teardown watchdog"""
        pass


class WatchDog(WatchDogBase):

    """Time-based watchdog

    Handles shared timer to detect stale services with outdated timestamps.
    """

    def __init__(self, heartbeat_timeout):
        super(WatchDog, self).__init__()
        self._heartbeat_channel = multiprocessing.Value(
            ctypes.c_int, int(time.time()),
        )
        self._heartbeat_timeout = heartbeat_timeout

    def _check_health(self):
        super(WatchDog, self)._check_health()
        with self._heartbeat_channel.get_lock():
            curr_time = time.time()
            last_heartbeat = self._heartbeat_channel.value
        delta = curr_time - last_heartbeat
        if delta >= self._heartbeat_timeout:
            raise exc.ServiceHeartbeatTimeout(timeout=self._heartbeat_timeout,
                                              delta=delta,
                                              last_heartbeat=last_heartbeat,
                                              check_time=curr_time)

    def generate_heartbeat(self):
        super(WatchDog, self).generate_heartbeat()
        with self._heartbeat_channel.get_lock():
            self._heartbeat_channel.value = int(time.time())
        self._l(LOG).debug("Heartbeat time record has been updated.")
