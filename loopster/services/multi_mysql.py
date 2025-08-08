# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2022 VK Cloud Solutions
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

from restalchemy.storage.sql import engines

from loopster.services import base_nested


RA_DEFAULT_ENGINE_NAME = engines.DEFAULT_NAME

LOG = logging.getLogger(__name__)


class MultiMySQLEngineUnit(object):

    def __init__(self, mysql_connection_url, mysql_config=None,
                 engine_name=RA_DEFAULT_ENGINE_NAME, query_cache=True,
                 ra_sender=None):
        super(MultiMySQLEngineUnit, self).__init__()
        self._engine_name = engine_name
        self._mysql_connection_url = engines.DBConnectionUrl(
            mysql_connection_url)
        self._mysql_config = mysql_config or {}
        self._query_cache = query_cache
        self._ra_sender = ra_sender

    def __str__(self):
        return "<%s::%s::%s::%s::%s::%s>" % (
            type(self),
            self.engine_name,
            self.mysql_connection_url,
            self.mysql_config,
            self.query_cache,
            self._ra_sender,
        )

    @property
    def engine_name(self):
        return self._engine_name

    @property
    def mysql_connection_url(self):
        return self._mysql_connection_url

    @property
    def mysql_config(self):
        return self._mysql_config.copy()

    @property
    def query_cache(self):
        return self._query_cache

    @property
    def ra_sender(self):
        return self._ra_sender


# TODO(d.burmistrov): handle missing mysql-connection - retry/exit 1?
class MultiMySQLStorageWrapper(base_nested.BaseNestedService):

    def __new__(cls, *args, **kwargs):
        inst = super(MultiMySQLStorageWrapper, cls).__new__(cls)
        inst._init_kwargs = kwargs
        return inst

    def __init__(self, *units, **kwargs):
        self._validate(units)
        super(MultiMySQLStorageWrapper, self).__init__(**kwargs)
        self._units = units

    @staticmethod
    def _validate(units):
        default = 0

        for unit in units:
            if unit.engine_name == RA_DEFAULT_ENGINE_NAME:
                default += 1
            if not isinstance(unit, MultiMySQLEngineUnit):
                raise TypeError("Unit must be MultiMySQLEngineUnit; got: %r"
                                % type(unit))

        if default != 1:
            raise ValueError("Exactly single default engine required; got: %d"
                             % default)

    def _setup(self):
        super(MultiMySQLStorageWrapper, self)._setup()
        self._l(LOG).info("Configuring multiple RA storages...")

        for unit in self._units:
            self._l(LOG).info("Setting unit: %s...", unit)
            engines.engine_factory.configure_factory(
                name=unit.engine_name,
                db_url=unit.mysql_connection_url.url,
                config=unit.mysql_config,
                query_cache=unit.query_cache,
                sender=unit.ra_sender,
            )
