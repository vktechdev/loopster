# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright 2020 Mail.ru Group.
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

import contextlib
import multiprocessing
import signal

from loopster.hubs.base import BaseHub
from loopster.hubs.drivers import process


class ProcessHub(BaseHub):
    """A class for managing services with one strategy by driver."""

    def __init__(self, controller):
        super(ProcessHub, self).__init__(driver=process.ProcessDriver(),
                                         controller=controller)
        self._signums = []

    def _subscribe_signals(self, handlers):
        """Define custom handlers to react on terminal actions."""

        handlers[signal.SIGHUP] = self._sighup_handler
        handlers[signal.SIGUSR1] = self._sigusr1_handler
        return super(ProcessHub, self)._subscribe_signals(handlers)

    def _sighup_handler(self, sig, frame):
        """Send signum SIGHUP to subprocesses."""

        with self._set_signums(sig):
            self._on_sighup()

    def _sigusr1_handler(self, sig, frame):
        """Send signum SIGUSR1 to subprocesses."""

        with self._set_signums(sig):
            self._on_sigusr1()

    @property
    def signum(self):
        """Return a signum for a subprocess."""

        signum = multiprocessing.Value("i", 0)
        self._signums.append(signum)
        return signum

    @contextlib.contextmanager
    def _set_signums(self, sig):
        """Set signal values to signums."""

        try:
            yield
        finally:
            for signum in self._signums:
                signum.value = sig.value
