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

import uuid


class Unit(object):

    def __init__(self, svc_class, svc_kwargs, state, unit_uuid=None):
        super(Unit, self).__init__()
        self._uuid = unit_uuid or uuid.uuid4()
        self._svc_class = svc_class
        # TODO(g.melikov): use something like ReadOnlyDictProxy from RA here
        self._svc_kwargs = svc_kwargs
        self._state = state

    def __repr__(self):
        return ("Unit(unit_uuid=%r, svc_class=%r, svc_kwargs=%r, state=%r)"
                % (self._uuid, self._svc_class, self._svc_kwargs, self._state))

    @property
    def uuid(self):
        return self._uuid

    @property
    def svc_class(self):
        return self._svc_class

    @property
    def svc_kwargs(self):
        return self._svc_kwargs  # TODO(d.burmistrov): read-only view

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value
