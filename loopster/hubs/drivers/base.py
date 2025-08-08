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
import logging

from loopster.common import obj
import six

from loopster import exceptions


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class AbstractDriver(obj.BaseObject):

    @abc.abstractmethod
    def validate_target_state(self, state):
        return NotImplementedError()

    @abc.abstractmethod
    def get_states(self):
        return NotImplementedError()

    @abc.abstractmethod
    def set_state(self, target_uuid, old_state, new_state):
        return NotImplementedError()

    @abc.abstractmethod
    def add_service(self, target_uuid, svc_class, svc_kwargs):
        return NotImplementedError()

    @abc.abstractmethod
    def remove_service(self, target_uuid):
        return NotImplementedError()

    @abc.abstractmethod
    def stop_service(self, target_uuid):
        return NotImplementedError()

    @abc.abstractmethod
    def stop_all_services(self):
        return NotImplementedError()

    @abc.abstractmethod
    def wait_service(self, target_uuid):
        return NotImplementedError()

    @abc.abstractmethod
    def wait_all_services(self):
        return NotImplementedError()


@six.add_metaclass(abc.ABCMeta)
class BaseDriver(AbstractDriver):
    """Base driver without actual work"""

    __target_states__ = set()

    def __init__(self):
        super(BaseDriver, self).__init__()
        self._services = {}

    def validate_target_state(self, state):
        """Validate if state is acceptable for this driver

        :param state: State
        :type state: enum:`loopster.states.State`

        :return: DriverUnsupportedState() on error
        """
        if state not in self.__target_states__:
            raise exceptions.DriverUnsupportedState(driver=self, state=state)

    @abc.abstractmethod
    def _get_service_state(self, target_uuid, svc_storage):
        return NotImplementedError()

    def get_states(self):
        """Return service states

        :param state: State
        :type state: enum:`loopster.states.State`

        return: a Dict with uuid:service_state
        """
        states_dict = {}
        for target_uuid, svc_storage in six.iteritems(self._services):
            states_dict[target_uuid] = (
                self._get_service_state(target_uuid, svc_storage))
        return states_dict

    @abc.abstractmethod
    def _set_state(self, target_uuid, old_state, new_state, svc_storage):
        raise NotImplementedError()

    def set_state(self, target_uuid, old_state, new_state):
        """Set service state, it will try to prepare and run service.

        :param target_uuid: Target UUID
        :type target_uuid: UUID
        :param old_state: Old state
        :type old_state: enum:`loopster.states.State`
        :param new_state: New state
        :type new_state: enum:`loopster.states.State`
        """
        self.validate_target_state(new_state)
        if new_state == old_state:
            return
        self._l(LOG).debug(
            "Changing state for target %s from %s to %s...",
            target_uuid, old_state, new_state)
        self._set_state(target_uuid, old_state, new_state,
                        self._services[target_uuid])

    @abc.abstractmethod
    def _get_service(self, target_uuid, svc_storage):
        raise NotImplementedError()

    @abc.abstractmethod
    def _add_service(self, target_uuid, svc_storage):
        raise NotImplementedError()

    def add_service(self, target_uuid, svc_class, svc_kwargs):
        """Add new service and store it inside driver

        :param target_uuid: Target UUID
        :type target_uuid: UUID
        :param svc_class: Service class to add
        :type svc_class: class:`loopster.services.base.AbstractService`
        :param svc_kwargs: optional keyword arguments for the service instance
        :type svc_kwargs: dict, optional
        """
        if target_uuid in self._services:
            raise exceptions.ServiceExists(target_uuid=target_uuid)
        # TODO(g.melikov): think about using object-like storage if needed
        svc_storage = {
            'svc_class': svc_class,
            'svc_kwargs': svc_kwargs,
        }
        self._add_service(target_uuid, svc_storage)
        self._services[target_uuid] = svc_storage
        self._l(LOG).info(
            "Added target %s for %r service with %s state",
            target_uuid,
            self._get_service(target_uuid, svc_storage),
            self._get_service_state(target_uuid, svc_storage))

    def remove_service(self, target_uuid):
        """Remove existing service from driver"""
        if target_uuid not in self._services:
            raise exceptions.ServiceNotFound(target_uuid=target_uuid)
        self._l(LOG).info("Removing target %s...", target_uuid)
        self._l(LOG).debug("Stopping target %s...", target_uuid)
        self._stop_service(target_uuid, self._services[target_uuid])
        self._l(LOG).debug("Waiting target %s...", target_uuid)
        self._wait_service(target_uuid, self._services[target_uuid])
        del self._services[target_uuid]
        self._l(LOG).info("Removed target %s", target_uuid)

    @abc.abstractmethod
    def _stop_service(self, target_uuid, svc_storage):
        raise NotImplementedError()

    def stop_service(self, target_uuid):
        """Stop existing service"""
        if target_uuid not in self._services:
            raise exceptions.ServiceNotFound(target_uuid=target_uuid)
        self._l(LOG).info("Stopping target %s...", target_uuid)
        self._stop_service(target_uuid, self._services[target_uuid])

    def stop_all_services(self):
        """Stop all services in driver"""
        self._l(LOG).info("Stopping all targets...")
        for target_uuid, svc_storage in six.iteritems(self._services):
            self._l(LOG).debug("Stopping target %s...", target_uuid)
            self._stop_service(target_uuid, svc_storage)

    @abc.abstractmethod
    def _wait_service(self, target_uuid, svc_storage):
        raise NotImplementedError()

    def wait_service(self, target_uuid):
        """Wait existing service to stop"""
        if target_uuid not in self._services:
            raise exceptions.ServiceNotFound(target_uuid=target_uuid)
        self._l(LOG).info("Waiting target %s...", target_uuid)
        self._wait_service(target_uuid, self._services[target_uuid])

    def wait_all_services(self):
        """Wait all existing services to stop"""
        self._l(LOG).info("Waiting all targets...")
        for target_uuid, svc_storage in six.iteritems(self._services):
            self._l(LOG).debug("Waiting target %s...", target_uuid)
            self._wait_service(target_uuid, svc_storage)
