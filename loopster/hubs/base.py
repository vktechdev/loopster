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

import copy
import logging

from loopster import exceptions
from loopster.services import softirq
from loopster import states
from loopster import units


LOG = logging.getLogger(__name__)


class BaseHub(softirq.SoftIrqService):
    """This object can manage many services with one strategy by driver.

    BaseHub is a SoftIrqService too itself.

    :param driver: preferred driver to use
    :type driver: class:`loopster.hubs.drivers.base.BaseDriver`
    :param controller: preferred controller to use
    :type controller: class:`loopster.hubs.controllers.base.AbstractController`
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
    """

    def __init__(self, driver, controller, step_period=1, loop_period=0.1,
                 sender=None, event_type=None, error_event_type=None,
                 watchdog=None):
        super(BaseHub, self).__init__(
            step_period=step_period,
            loop_period=loop_period,
            sender=sender,
            event_type=event_type,
            error_event_type=error_event_type,
            watchdog=watchdog,
        )
        self._units = {}
        self._driver = driver
        self._controller = controller

    def _get_unit(self, unit_uuid):
        try:
            return self._units[unit_uuid]
        except KeyError:
            raise exceptions.UnitNotFound(unit_uuid=unit_uuid)

    def get_target_states(self):
        """Get target states of services

        :return: a Dict with {unit.uuid: unit:state} key: values
        """
        return {unit.uuid: unit.state for unit in self._units.values()}

    def add_unit(self, unit):
        """Add unit to serve

        :param unit: Unit to add
        :type unit: class:`loopster.units.Unit`
        """
        if unit.uuid in self._units:
            raise exceptions.UnitExists(unit_uuid=unit.uuid)
        self._driver.validate_target_state(unit.state)
        new_unit = copy.copy(unit)
        self._driver.add_service(
            new_unit.uuid, new_unit.svc_class, new_unit.svc_kwargs)
        self._units[unit.uuid] = new_unit
        self._l(LOG).info("Unit was added: %r", new_unit)
        return copy.copy(self._units[unit.uuid])

    def update_unit(self, unit):
        """Update unit. Only state update is supported for now.

        :param unit: Unit to update
        :type unit: class:`loopster.units.Unit`
        """
        _unit = self._get_unit(unit.uuid)
        self._driver.validate_target_state(unit.state)
        if (_unit.svc_class != unit.svc_class
                or _unit.svc_kwargs != unit.svc_kwargs):
            raise ValueError(
                'New unit has different class or kwargs: '
                'new class: %s, kwargs: %s, old: %s, %s' %
                (unit.svc_class, unit.svc_kwargs, _unit.svc_class,
                 _unit.svc_kwargs))
        old_state = _unit.state
        _unit.state = unit.state
        self._l(LOG).info("Unit %s was updated from %r to %r",
                          _unit.uuid, old_state, _unit.state)
        return unit

    def remove_unit(self, unit):
        """Remove unit

        :param unit: Unit to remove
        :type unit: class:`loopster.units.Unit`
        """
        if unit.uuid not in self._units:
            raise exceptions.UnitNotFound(unit_uuid=unit.uuid)
        self._driver.remove_service(unit.uuid)
        del self._units[unit.uuid]
        self._l(LOG).info("Unit was removed: %r", unit)

    def _step(self):
        self._l(LOG).debug("Managing state...")
        try:
            self._controller.manage(self, self._driver)
        except exceptions.StopHub as e:
            self._l(LOG).info(e)
            self.stop()
        except Exception:
            self.stop()
            raise

    def add_service(self,
                    svc_class,
                    svc_kwargs=None,
                    state=states.State.RUNNING):
        """Add service to serve. Wrapper on add_unit().

        :param svc_class: Service class to add
        :type svc_class: class:`loopster.services.base.AbstractService`
        :param svc_kwargs: Service to add
        :type svc_kwargs: dict, optional
        :param state: Service state, defaults to State.RUNNING
        :type state: enum:`loopster.states.State`
        """
        svc_kwargs = svc_kwargs or {}
        return self.add_unit(units.Unit(svc_class, svc_kwargs, state))

    def _shutdown(self):
        self._l(LOG).info("Shutting down...")
        self._l(LOG).info("Stopping all services...")
        self._driver.stop_all_services()
        self._l(LOG).info("Waiting all services...")
        self._driver.wait_all_services()
        # TODO(g.melikov): think about zombies cleanup here
        # multiprocessing.active_children()  # join all

    def _teardown(self):
        self._shutdown()
        super(BaseHub, self)._teardown()

    def stop(self):
        """Stop BaseHub service cycle"""
        self._l(LOG).info("Stopping...")
        self._controller.stop(self._driver)
        super(BaseHub, self).stop()
