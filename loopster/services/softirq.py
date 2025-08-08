# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright 2019-2021 Mail.ru Group.
#
#    All Rights Reserved.
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

import abc
import contextlib
import ctypes
import ctypes.util
import datetime
import logging
import os
import signal
import sys
import time
import uuid

from loopster.common import exc as iaas_exc
import six

from loopster.services import base
from loopster.watchdogs import exceptions as wd_exc

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None


LOG = logging.getLogger(__name__)


@contextlib.contextmanager
def _measure(step_info):
    start = datetime.datetime.utcnow()
    try:
        yield
    finally:
        end = datetime.datetime.utcnow()
        step_info['start'] = start
        step_info['end'] = end
        step_info['timestamp'] = end
        step_info['duration'] = end - start


@contextlib.contextmanager
def _excs(excs):
    try:
        yield
    except Exception:
        exc_info = sys.exc_info()
        excs.append(exc_info)
        raise


@six.add_metaclass(abc.ABCMeta)
class SoftIrqService(base.AbstractService):
    """The Soft IRQ service with watchdog on steroids.


    Subscriptions on some signals for a graceful shutdown.
    Just run infinite cycle in step() until stopped. A watchdog defines the
    behavior of the service between steps.

    :param watchdog: the watchdog object
    :type watchdog: class:`loopster.hubs.watchdogs.watchdog.WatchDog`
    :param step_period: minimal period of step before start next one,
        defaults to 1
    :type step_period: float, optional
    :param loop_period: pause between each steps, defaults to 0.1
    :type loop_period: float, optional
    :param sender: Sender to use in Camel
    :type sender: class:`camel.senders.DPPSender`, optional
    :param event_type: Event type for camel sender
    :type event_type: str, optional
    :param error_event_type: Error event type for camel sender
    :type error_event_type: str, optional
    :param operate: Allows to manage running of service from environment
     variables
    :type operate: bool, optional
    :param signum: Signal number sent to this service
    :type signum: multiprocessing.Value, optional
    """

    SERVICE_TYPE = 'soft_irq'

    PR_SET_PDEATHSIG = 1

    def __init__(self, step_period=1, loop_period=0.1, sender=None,
                 event_type=None, error_event_type=None, watchdog=None,
                 operate=True, signum=None):
        super(SoftIrqService, self).__init__(watchdog=watchdog,
                                             operate=operate)
        self._has_running = False
        self._next_step_delta = None
        self._step_period = step_period
        self._loop_period = loop_period
        self._launch_id = None
        self._pid = None
        self._iteration_number = 0
        self._sender = sender
        self._event_type = self._get_event_type(event_type)
        self._error_event_type = self._get_error_event_type(error_event_type)
        self._wderr_event_type = self._event_type + ".watchdog_context_error"
        self._signum = signum
        self._signum_handlers = {
            signal.SIGHUP: self._on_sighup,
            signal.SIGUSR1: self._on_sigusr1,
        }

    def _set_pdeathsig(self):
        self._l(LOG).debug(
            "Set PR_SET_PDEATHSIG %d for process pid: %d, parent pid: %d",
            self.PR_SET_PDEATHSIG,
            os.getpid(),
            os.getppid(),
        )
        if self.PR_SET_PDEATHSIG == 0:
            return

        libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        if libc.prctl(self.PR_SET_PDEATHSIG, signal.SIGKILL) != 0:
            raise OSError(ctypes.get_errno(), "SET_PDEATHSIG")

    def _get_event_type(self, event_type):
        if event_type:
            return event_type
        event_type = '.'.join([type(self).__name__,
                               'service',
                               self.SERVICE_TYPE,
                               'iteration_step'])
        return event_type

    def _get_error_event_type(self, error_event_type):
        if error_event_type:
            return error_event_type
        error_event_type = self._event_type + '.error'
        return error_event_type

    def _send_event(self, event_data):
        if self._sender is None:
            self._l(LOG).debug("no sender - skipping event: %s", event_data)
        else:
            self._sender.send_event(event_data)

    def _send_step_event(self, event_data):
        event_data.setdefault('event_type', self._event_type)
        self._send_event(event_data)

    def _send_exc_step_event(self, exc_event_data):
        exc_event_data.setdefault('event_type', self._error_event_type)
        self._send_event(exc_event_data)

    def _send_wd_error_event(self, wderr_event_data):
        wderr_event_data.setdefault('event_type', self._wderr_event_type)
        self._send_event(wderr_event_data)

    def _make_step_info(self):
        return {
            'iteration': self._iteration_number,
            'step_period': self._step_period,
            'service': type(self).__name__,
            'service_type': self.SERVICE_TYPE,
            'pid': self._pid,
            'launch_id': self._launch_id,
            'skipped':  True,
        }

    def _sentry_capture_exception(self, error):
        if sentry_sdk:
            sentry_sdk.capture_exception(error)

    def _loop_step(self):
        iteration = self._iteration_number
        step_info = self._make_step_info()
        excs = []
        wd_error = None
        try:
            self._on_signum()
            self._l(LOG).debug("Starting iteration number %d", iteration)
            with _measure(step_info):
                with self._watchdog:
                    step_info['skipped'] = False
                    with _excs(excs):
                        self._wrapped_step(step_info)
            self._l(LOG).debug(
                "Finished iteration number %d in %0.5f seconds",
                iteration, step_info['duration'].total_seconds())
            with iaas_exc.suppress_any():
                self._watchdog.generate_heartbeat()
        except Exception:
            exc_info = sys.exc_info()

            # <watchdog exception>
            #
            # watchdog error conditions & states:
            #     "__enter__ exception"
            #   or
            #     "__exit__ exception when step succeeded"
            #   or
            #     "__exit__ exception when step failed" (different exceptions)
            if (step_info['skipped']
                    or (not excs)
                    or (exc_info[1] is not excs[0][1])):
                wd_error = exc_info
                # ignore minor exception & generate heartbeat
                if isinstance(wd_error[1], wd_exc.WatchDogMinorException):
                    self._l(LOG).debug(
                        "Ignoring minor watchdog error on iteration %d: %r",
                        iteration, wd_error[1])
                    with iaas_exc.suppress_any():
                        self._watchdog.generate_heartbeat()
                # log critical or unknown exceptions but do NOT heartbeat
                else:
                    self._l(LOG).log(
                        logging.ERROR,
                        "Unexpected watchdog exception within iteration %d:",
                        iteration,
                        exc_info=wd_error)
                    self._sentry_capture_exception(wd_error[1])

            # <step exception>
            if excs:
                self._l(LOG).log(
                    logging.ERROR,
                    "Unexpected step error during iteration number %d",
                    iteration,
                    exc_info=excs[0])
                self._sentry_capture_exception(excs[0][1])
        finally:
            # base event
            step_event = step_info.copy()
            step_event['tb'] = bool(excs)
            self._send_step_event(step_event)
            # on exception event
            if excs:
                step_error_event = step_info.copy()
                step_error_event['error_type'] = excs[0][0]
                step_error_event['error'] = repr(excs[0][1])
                self._send_exc_step_event(step_error_event)
            # watchdog event
            if wd_error is not None:
                watchdog_error_event = step_info.copy()
                watchdog_error_event['minor'] = isinstance(
                    wd_error[1], wd_exc.WatchDogMinorException)
                watchdog_error_event['error_type'] = wd_error[0]
                watchdog_error_event['error'] = repr(wd_error[1])
                self._send_wd_error_event(watchdog_error_event)
            # routine
            self._iteration_number += 1

    def _serve(self):
        self._has_running = True
        next_step_time = 0
        while self._has_running:
            current_time = time.time()

            if current_time >= next_step_time:
                next_step_time = current_time + self._step_period
                self._loop_step()

            if self._next_step_delta is not None:
                next_step_time = time.time() + self._next_step_delta
                self._next_step_delta = None

            if self._loop_period == 0:
                # just wait for next step efficiently
                time_to_sleep = next_step_time - time.time()
                if time_to_sleep > 0:
                    time.sleep(time_to_sleep)
            else:
                time.sleep(self._loop_period)

    def _setup(self):
        super(SoftIrqService, self)._setup()
        self._launch_id = str(uuid.uuid4())
        self._pid = os.getpid()
        self._set_pdeathsig()

    def _teardown(self):
        super(SoftIrqService, self)._teardown()
        self._launch_id = None
        self._pid = None
        self._l(LOG).info("Service has been stopped")

    def _schedule_next_step(self, delta):
        self._l(LOG).info("Rescheduling next step time with delta=%f", delta)
        self._next_step_delta = delta

    def _wrapped_step(self, step_info):
        return self._step()

    def _on_sighup(self):
        """React on signum == SIGHUP."""

        pass

    def _on_sigusr1(self):
        """React on signum == SIGUSR1.

        Toggle a logging level depending on its  current one.
        """

        root_logger = logging.getLogger()
        if root_logger.level == logging.INFO:
            root_logger.setLevel(logging.DEBUG)
        elif root_logger.level == logging.DEBUG:
            root_logger.setLevel(logging.INFO)

    def _on_signum(self):
        """React on signum."""

        if self._signum and self._signum.value != 0:
            signum_handler = self._signum_handlers.get(self._signum.value)
            if signum_handler:
                signum_handler()
            self._signum.value = 0

    def _subscribe_signums(self, handlers):
        """Override signum handlers."""

        self._signum_handlers.update(handlers)

    @abc.abstractmethod
    def _step(self):
        raise NotImplementedError()

    def stop(self):
        """Stop service"""
        self._l(LOG).info("Stopping...")
        self._has_running = False
