# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#   Copyright 2019 Mail.ru Group
#   Copyright 2020 Mail.ru Group
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

from __future__ import absolute_import

import abc
import logging
import os
import signal

import bjoern
import six

from loopster.services import base


LOG = logging.getLogger(__name__)


class BjoernSingletonMeta(abc.ABCMeta):

    _INSTANCES = {}

    def __call__(cls, *args, **kwargs):
        port = int(kwargs['port'])
        if port in cls._INSTANCES:
            return cls._INSTANCES[port]
        instance = super(BjoernSingletonMeta, cls).__call__(*args, **kwargs)
        cls._INSTANCES[port] = instance
        return instance


@six.add_metaclass(BjoernSingletonMeta)
class BjoernService(base.AbstractService):
    """Special server for Bjoern, it implements multiprocessing by itself"""

    def __init__(self, wsgi_app, host, port, bjoern_kwargs=None,
                 operate=True):
        super(BjoernService, self).__init__(operate=operate)
        self._host = host
        self._port = port
        bjoern_kwargs = bjoern_kwargs or {}
        bjoern_kwargs.setdefault('reuse_port', False)
        bjoern.listen(wsgi_app=wsgi_app, host=host, port=port, **bjoern_kwargs)

    @property
    def subscribe_signals(self):
        return True

    def _get_signal_handlers(self):
        def sigterm_to_sigint(s, frame):
            os.kill(os.getpid(), signal.SIGINT)

        return {
            signal.SIGTERM: sigterm_to_sigint
        }

    # As Bjoern has gracefully shut down it calls
    # PyErr_SetInterrupt function. It calls python signal handler as
    # callable object for Python 2.7. But it fails for SIG_DFL
    # and SIG_IGN values. To avoid setting of SIG_IGN with default
    # AbstractService._subscribe_signals implementation this class
    # implements signal subscription only for certain signals.
    def _subscribe_signals(self, handlers):
        if self._sig_subscribed:
            raise RuntimeError("Already subscribed signals")

        # wrap handlers
        handlers = {s: self._wrap(h)
                    for s, h in handlers.items()}

        # subscribe
        for s, h in handlers.items():
            signal.signal(s, h)

        self._sig_subscribed = True

    def _serve(self):
        self._l(LOG).info('Bjoern server socket: %s:%s',
                          self._host, self._port)
        bjoern.run()

    def stop(self):
        raise NotImplementedError()
