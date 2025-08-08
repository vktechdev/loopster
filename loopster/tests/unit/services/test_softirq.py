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

import logging
import multiprocessing
import unittest

import mock

from loopster.services import softirq
from loopster.watchdogs import exceptions as wdxc

LOG = logging.getLogger(__name__)

FAKE_WD_MINOR_EXCEPTION = wdxc.WatchDogMinorException(reason="Fake error")


class TestService(softirq.SoftIrqService):

    def _step(self):
        pass


class TestServiceEventualStop(softirq.SoftIrqService):
    count_to_stop = 5

    def _step(self):
        self.count_to_stop -= 1
        if self.count_to_stop < 1:
            self.stop()


class SoftIRQLoopStepMinorWatchdogErrorInTryTestCase(unittest.TestCase):

    @mock.patch('loopster.services.softirq.SoftIrqService._send_wd_error_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_exc_step_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_step_event')
    @mock.patch('loopster.watchdogs.base.WatchDogBase.__enter__')
    def test_error_only_enter(self, enter, send, err_send, wd_send):
        enter.side_effect = FAKE_WD_MINOR_EXCEPTION
        s = TestService()
        s._loop_step()

        send.assert_called_once()
        err_send.assert_not_called()
        wd_send.assert_called_once()

    @mock.patch('loopster.services.softirq.SoftIrqService._send_wd_error_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_exc_step_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_step_event')
    @mock.patch('loopster.watchdogs.base.WatchDogBase.__exit__')
    def test_error_only_exit(self, exit, send, err_send, wd_send):
        exit.side_effect = FAKE_WD_MINOR_EXCEPTION
        s = TestService()
        s._loop_step()

        send.assert_called_once()
        err_send.assert_not_called()
        wd_send.assert_called_once()

    @mock.patch('loopster.services.softirq.SoftIrqService._send_wd_error_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_exc_step_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_step_event')
    def test_error_only_step(self, send, err_send, wd_send):
        s = TestService()
        with mock.patch.object(s,
                               '_step',
                               side_effect=FAKE_WD_MINOR_EXCEPTION):
            s._loop_step()

        send.assert_called_once()
        err_send.assert_called_once()
        wd_send.assert_not_called()

    @mock.patch('loopster.services.softirq.SoftIrqService._send_wd_error_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_exc_step_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_step_event')
    @mock.patch('loopster.watchdogs.base.WatchDogBase.__exit__')
    def test_error_exit_and_step(self, exit, send, err_send, wd_send):
        exit.side_effect = FAKE_WD_MINOR_EXCEPTION
        s = TestService()
        with mock.patch.object(s,
                               '_step',
                               side_effect=wdxc.WatchDogMinorException):
            s._loop_step()

        send.assert_called_once()
        err_send.assert_called_once()
        wd_send.assert_called_once()

    @mock.patch('loopster.services.softirq.SoftIrqService._send_wd_error_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_exc_step_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_step_event')
    @mock.patch('loopster.watchdogs.base.WatchDogBase.__enter__')
    def test_error_enter_and_step(self, enter, send, err_send, wd_send):
        enter.side_effect = FAKE_WD_MINOR_EXCEPTION
        s = TestService()
        with mock.patch.object(s,
                               '_step',
                               side_effect=wdxc.WatchDogMinorException):
            s._loop_step()

        send.assert_called_once()
        err_send.assert_not_called()
        wd_send.assert_called_once()

    @mock.patch('loopster.services.softirq.SoftIrqService._send_wd_error_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_exc_step_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_step_event')
    @mock.patch('loopster.watchdogs.base.WatchDogBase.__exit__')
    @mock.patch('loopster.watchdogs.base.WatchDogBase.__enter__')
    def test_error_all(self, enter, exit, send, err_send, wd_send):
        enter.side_effect = FAKE_WD_MINOR_EXCEPTION
        exit.side_effect = FAKE_WD_MINOR_EXCEPTION
        s = TestService()
        with mock.patch.object(s,
                               '_step',
                               side_effect=wdxc.WatchDogMinorException):
            s._loop_step()

        send.assert_called_once()
        err_send.assert_not_called()
        wd_send.assert_called_once()

    @mock.patch('loopster.services.softirq.SoftIrqService._serve_fake')
    @mock.patch('loopster.services.softirq.SoftIrqService._serve_operational')
    def test_only_step_enabled(self, serve_operational, serve_fake):
        s = TestService()

        s.serve()

        serve_operational.assert_called_once()
        serve_fake.assert_not_called()

    @mock.patch('loopster.services.softirq.SoftIrqService._serve_fake')
    @mock.patch('loopster.services.softirq.SoftIrqService._serve_operational')
    def test_only_step_not_enabled(self, serve_operational, serve_fake):
        s = TestService(operate=False)

        s.serve()

        serve_operational.assert_not_called()
        serve_fake.assert_called_once()

    @mock.patch('loopster.services.softirq.SoftIrqService._send_wd_error_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_exc_step_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._send_step_event')
    @mock.patch('loopster.services.softirq.SoftIrqService._on_sighup')
    def test_loop_step_error_only_step_and_signum(self, on_sighup, send,
                                                  err_send, wd_send):
        s = TestService(signum=multiprocessing.Value("i", 0))
        for signum in (0, 1, 10):
            s._signum.value = signum
            with mock.patch.object(s,
                                   '_step',
                                   side_effect=FAKE_WD_MINOR_EXCEPTION):
                s._loop_step()
                self.assertEqual(0, s._signum.value)

        on_sighup.assert_called_once()
        self.assertEqual(3, send.call_count)
        self.assertEqual(3, err_send.call_count)
        wd_send.assert_not_called()

    @mock.patch('time.sleep', return_value=None)
    def test_loop_period_positive(self, time_sleep):
        s = TestServiceEventualStop(step_period=0, loop_period=1)

        s.serve()

        calls = [mock.call(1)] * 5
        time_sleep.assert_has_calls(calls)
        assert time_sleep.call_count == 5

    @mock.patch('time.sleep', return_value=None)
    def test_loop_period_zero_not_slept(self, time_sleep):
        s = TestServiceEventualStop(step_period=0, loop_period=0)

        s.serve()

        time_sleep.assert_not_called()

    @mock.patch('time.sleep', return_value=None)
    def test_loop_period_zero_wait_for_next_step(self, time_sleep):
        s = TestServiceEventualStop(step_period=0.01, loop_period=0)

        s.serve()

        assert 0 < time_sleep.call_args[0][0] < 0.01
        assert time_sleep.call_count > 10
