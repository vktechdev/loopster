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


class LoopsterException(Exception):

    """Base Loopster Exception.

    To correctly use this class, inherit from it and define 'msg_template'
    class attribute. That template will be formatted with provided keyword
    arguments.
    """

    msg_template = "An unknown exception occurred."

    def __init__(self, **kwargs):
        self._kwargs = kwargs
        super(LoopsterException, self).__init__()

    def __repr__(self):
        qual_name = '%s.%s' % (self.__module__, type(self).__name__)
        kwargs = ', '.join('%s=%r' % (k, v) for k, v in self._kwargs.items())
        return '%s(%s)' % (qual_name, kwargs)

    def __str__(self):
        return self.msg_template % self._kwargs

    @property
    def message(self):
        return str(self)

    @property
    def kwargs(self):
        return self._kwargs.copy()  # TODO(d.burmistrov): use view-proxy

    @property
    def args(self):
        raise NotImplementedError("Not supported; use `kwargs` instead")


class StopHub(LoopsterException):

    msg_template = "Stop hub by reason: %(reason)s."


class UnitExists(LoopsterException):

    msg_template = "Unit with %(unit_uuid)r uuid already exists."


class UnitNotFound(LoopsterException):

    msg_template = "Unit with %(unit_uuid)r uuid is not found."


class ServiceNotFound(LoopsterException):

    msg_template = "Service with %(target_uuid)r id is not found."


class ServiceExists(LoopsterException):

    msg_template = "Service with %(target_uuid)r id already exists."


class DriverUnsupportedState(LoopsterException):

    msg_template = "Driver %(driver)r doesn't support %(state)r state."


class ServiceWaitTimeoutError(LoopsterException):
    msg_template = "Service %(target_uuid)s wait timed out after %(timeout)d."


class UnexpectedServiceState(LoopsterException):
    msg_template = "Service %(target_uuid)s is in illegal state %(state)s."
