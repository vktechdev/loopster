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

import collections
import logging
import multiprocessing as mp
import os
import sys

from loopster import exceptions
from loopster.hubs.drivers import base
from loopster import states


LOG = logging.getLogger(__name__)

FORCIBLY_STOPPED_KEY = 'forcibly_stopped'
SERVICE_KEY = 'service'
SERVICE_CLASS_KEY = 'svc_class'
SERVICE_KWARGS_KEY = 'svc_kwargs'
PROCESS_KEY = 'process'
FORK_START_METHOD = 'fork'
# In Python 3.8 default start method at Mac was changed from 'fork' to 'spawn'
PYTHON_VERSION_CHANGED_START_METHOD = (3, 8)


class ProcessDriver(base.BaseDriver):
    """Driver to serve services as via child processes"""
    __target_states__ = {states.State.RUNNING,
                         states.State.STOPPED}

    def __init__(self):
        super(ProcessDriver, self).__init__()
        self._setup()
        self._state_map = collections.defaultdict(
            lambda: collections.defaultdict(
                lambda: self._default_state_handler))
        self._state_map.update({
            states.State.INITIAL: {
                states.State.RUNNING: self._start_state_handler,
                states.State.STOPPED: self._set_stopped_state_handler,
            },
            states.State.RUNNING: {
                states.State.STOPPED: self._stop_state_handler,
            },
            states.State.STOPPED: {
                states.State.RUNNING: self._start_again_state_handler,
            },
            states.State.FAILED: {
                states.State.RUNNING: self._start_again_state_handler,
                states.State.STOPPED: self._set_stopped_state_handler,
            },
            states.State.NUMB: {
                states.State.RUNNING: self._kill_and_restart_handler,
                states.State.STOPPED: self._kill_state_handler,
            },
        })
        # TODO(g.melikov): add signals

    def _setup(self):
        """Prepares driver for working at OS with not default start method.

        There are different start_method of process in multiprocessing
        at non-linux OS. So, this method needs to configure context of
        multiprocessing at other OS, for example MacOS.

        :return: NoReturn, just changes method for creating new child
            process
        """
        if (sys.platform == 'darwin'
                and sys.version_info >= PYTHON_VERSION_CHANGED_START_METHOD):
            mp.set_start_method(FORK_START_METHOD)

    # utility methods

    @staticmethod
    def _init_service(target_uuid, svc_storage):
        """Prepares service constrictor and initializes it in subprocess.

        Passes talkback_channel only to services subclassed from SoftIrqService
        for backward-compatibility

        :param target_uuid:
        :param svc_storage:
        """
        svc = svc_storage[SERVICE_CLASS_KEY](**svc_storage[SERVICE_KWARGS_KEY])
        int_state = {
            SERVICE_KEY: svc,
            PROCESS_KEY: mp.Process(target=svc.serve),
            FORCIBLY_STOPPED_KEY: False,
        }
        svc_storage.update(int_state)

    def _get_service(self, target_uuid, svc_storage):
        return svc_storage[SERVICE_KEY]

    # worker & state transition processing

    def _set_state(self, target_uuid, old_state, new_state, svc_storage):
        self._state_map[old_state][new_state](
            target_uuid, old_state, new_state, svc_storage)

    def _default_state_handler(
            self, target_uuid, old_state, new_state, svc_storage):
        raise NotImplementedError()

    def _start_state_handler(
            self, target_uuid, old_state, new_state, svc_storage):
        svc_storage[PROCESS_KEY].start()

    def _start_again_state_handler(
            self, target_uuid, old_state, new_state, svc_storage):
        cur_state = self._get_process_state(svc_storage[PROCESS_KEY])
        if cur_state is states.State.RUNNING:
            raise exceptions.UnexpectedServiceState(target_uuid=target_uuid,
                                                    state=cur_state)
        self._init_service(target_uuid, svc_storage)
        self._start_state_handler(
            target_uuid, old_state, new_state, svc_storage
        )

    def _set_stopped_state_handler(
            self, target_uuid, old_state, new_state, svc_storage):
        svc_storage[FORCIBLY_STOPPED_KEY] = True

    def _stop_state_handler(
            self, target_uuid, old_state, new_state, svc_storage):
        self._stop_service(target_uuid, svc_storage)

    def _kill_state_handler(
            self, target_uuid, old_state, new_state, svc_storage):
        cur_state = self._get_process_state(svc_storage[PROCESS_KEY])
        if cur_state is not states.State.RUNNING:
            # It shouldn't happen, but if it would - we should notice
            self._l(LOG).error(
                'Tried to kill and restart an innocent service'
            )
            return
        self._kill_service(target_uuid, svc_storage)

    def _kill_and_restart_handler(
            self, target_uuid, old_state, new_state, svc_storage):
        self._kill_state_handler(
            target_uuid, old_state, new_state, svc_storage
        )
        svc_state = self._get_process_state(svc_storage[PROCESS_KEY])
        if svc_state is states.State.RUNNING:
            raise exceptions.UnexpectedServiceState(target_uuid=target_uuid,
                                                    state=svc_state)
        self._init_service(target_uuid, svc_storage)
        self._start_state_handler(
            target_uuid, old_state, new_state, svc_storage
        )

    # sensor

    @staticmethod
    def _get_process_state(process):
        """Actual process state retrieval

        :param mp.Process process: Multiprocessing Process reference
        """

        if process.pid is None:
            return states.State.INITIAL

        code = process.exitcode
        if code is None:
            return states.State.RUNNING
        # Correct stop is only exit 0 or our SIGTERM signal from driver
        elif code in [-15, 0]:
            return states.State.STOPPED
        else:
            return states.State.FAILED

    def _override_service_state(self, target_uuid, svc_storage, real_state):
        # 1. if driver internally marks service as STOPPED - stick with it
        #      watchdog checkup is skipped because we trust our code to set
        #      this manual mark only in safe places during execution flow
        if (svc_storage[FORCIBLY_STOPPED_KEY]
                and (real_state is not states.State.RUNNING)):
            return states.State.STOPPED

        # 2. running services with stale watchdog are treated as NUMB
        if real_state is states.State.RUNNING:
            svc = self._get_service(target_uuid, svc_storage)
            if not svc.get_watchdog().is_alive():
                return states.State.NUMB

        return real_state

    def _get_service_state(self, target_uuid, svc_storage):
        svc_state = self._get_process_state(svc_storage[PROCESS_KEY])
        svc_state = self._override_service_state(
            target_uuid, svc_storage, svc_state)
        return svc_state

    # service management (from hub/controller)

    def _add_service(self, target_uuid, svc_storage):
        self._init_service(target_uuid, svc_storage)

    def _stop_service(self, target_uuid, svc_storage):
        process = svc_storage[PROCESS_KEY]
        try:
            process.terminate()
        except OSError as e:  # Process doesn't exist
            self._l(LOG).warning(
                "Failed to terminate process pid=%s, service=%r: %r",
                process.pid, self._get_service(target_uuid, svc_storage), e)

    def _kill_service(self, target_uuid, svc_storage):
        process = svc_storage[PROCESS_KEY]
        try:
            os.kill(process.pid, 9)
            self._wait_service(target_uuid, svc_storage, timeout=0.1)
        except OSError as e:
            self._l(LOG).warning(
                "Failed to kill process pid=%s, service=%r: %r",
                process.pid, self._get_service(target_uuid, svc_storage), e)

    def _wait_service(self, target_uuid, svc_storage, timeout=None):
        process = svc_storage[PROCESS_KEY]
        try:
            process.join(timeout=timeout)
            if process.is_alive():
                self._l(LOG).warning("Timed out on joining service process "
                                     "%d after %ds.",
                                     process.pid, timeout
                                     )
        except AssertionError as e:
            if str(e) != 'can only join a started process':
                raise
