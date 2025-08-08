# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2019 Mail.ru Group
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

import logging

from loopster.services import base


LOG = logging.getLogger(__name__)


class BaseNestedService(base.AbstractService):
    def __init__(self, nested_class, nested_kwargs, operate=True):
        super(BaseNestedService, self).__init__(operate=operate)
        self._nested_class = nested_class
        self._nested_kwargs = nested_kwargs
        self._nested_service = self._nested_class(**self._nested_kwargs)
        self._l(LOG).info("Instantiated nested service %r",
                          self._nested_service)

    @property
    def subscribe_signals(self):
        return False

    @subscribe_signals.setter
    def subscribe_signals(self, value):
        msg = "Proxying 'subscribe_signals=%r' request to nested service..."
        self._l(LOG).info(msg, value)
        self._nested_service.subscribe_signals = value

    def _serve(self):
        self._l(LOG).info("Serving nested service...")
        self._nested_service.serve()

    def stop(self):
        self._l(LOG).info("Stopping nested service...")
        self._nested_service.stop()
