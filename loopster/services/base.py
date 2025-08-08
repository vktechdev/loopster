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

import abc
import copy
import logging
import signal
import sys

from loopster.common import obj
import six

from loopster import sig
from loopster.watchdogs import base as wd_base


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class AbstractService(obj.BaseObject):

    """Main loop signal-aware abstract service

    `_serve()` should be infinite loop
    `operate` allows to manage running of service from environment variables
    """

    def __init__(self, watchdog=None, operate=True):
        super(AbstractService, self).__init__()
        self._sig_subscribed = False
        self._subscribe_signals_flag = True
        self._watchdog = copy.copy(watchdog) or wd_base.WatchDogBase()
        self._operate = operate

    def get_watchdog(self):
        return self._watchdog

    @property
    def subscribe_signals(self):
        return self._subscribe_signals_flag

    @subscribe_signals.setter
    def subscribe_signals(self, value):
        """Set signal subscription flag

        :param value: subscription flag
        :type value: bool
        """
        self._l(LOG).info("Setting subscribe_signals=%r...", value)
        self._subscribe_signals_flag = value

    def _setup(self):
        pass

    def _teardown(self):
        self._watchdog.teardown()

    def _serve_fake(self):
        """Fake serving"""
        self._l(LOG).info("Serving is not started."
                          " Operate is not enabled!")
        if self.subscribe_signals:
            def exit_callback(s, frame):
                return sys.exit()

            handlers = {
                signal.SIGINT: exit_callback,
                signal.SIGTERM: exit_callback,
            }
            self._subscribe_signals(handlers=handlers)
        signal.pause()

    def _serve_operational(self):
        """Method to do actual job"""
        try:
            self._l(LOG).info("Preparing to serve...")
            self._setup()
            if self.subscribe_signals:
                self._subscribe_signals(self._get_signal_handlers())
            self._l(LOG).info("Serving...")
            self._serve()
            self._l(LOG).info("Finished serving normally.")
        finally:
            self._l(LOG).info("Tearing down...")
            self._teardown()

    def serve(self):
        if self._operate:
            self._serve_operational()
        else:
            self._serve_fake()

    @abc.abstractmethod
    def _serve(self):  # TODO(d.burmistrov): what about "serve info"?
        """Private method to override by each service implementation"""
        raise NotImplementedError()

    @abc.abstractmethod
    def stop(self):
        """Stop service"""
        raise NotImplementedError()

    # signals

    def _get_signal_handlers(self):
        def stop_callback(s, frame):
            self.stop()

        base_handlers = {
            signal.SIGINT: stop_callback,
            signal.SIGTERM: stop_callback,
        }

        return base_handlers

    def _wrap(self, func):
        @six.wraps(func)
        def wrapper(signum, frame):
            s = sig.Signals(signum)
            self._l(LOG).info("Received %s:%d signal", s.name, s.value)
            func(s, frame)
        return wrapper

    def _subscribe_signals(self, handlers):
        if self._sig_subscribed:
            raise RuntimeError("Already subscribed signals")

        _handlers = {
            signal.SIG_DFL: 'SIG_DFL',
            signal.SIG_IGN: 'SIG_IGN',
        }

        # wrap handlers
        handlers = {s: self._wrap(h)
                    for s, h in handlers.items()
                    if h not in _handlers}

        # default handlers
        handlers.setdefault(signal.SIGCHLD, signal.SIG_DFL)
        inv_signals = {s.value: s.name for s in sig.Signals}
        for s in (set(inv_signals.keys()) - {signal.SIGKILL, signal.SIGSTOP}):
            handlers.setdefault(s, signal.SIG_IGN)

        # subscribe
        for s, h in handlers.items():
            signal.signal(s, h)

        self._sig_subscribed = True
        self._l(LOG).info(
            "Subscribed signals: %s",
            ", ".join(
                "%s:%s" % (inv_signals.get(s, s), _handlers.get(h, h))
                for s, h in handlers.items()))
