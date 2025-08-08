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

from restalchemy.storage.sql import engines

from loopster.services import base_nested


LOG = logging.getLogger(__name__)


# TODO(d.burmistrov): handle missing mysql-connection - retry/exit 1?
class MySQLStorageWrapper(base_nested.BaseNestedService):

    def __init__(self, mysql_connection_url, mysql_config=None,
                 ra_sender=None, **kwargs):
        if not isinstance(mysql_connection_url, engines.DBConnectionUrl):
            raise TypeError("Connection URL must be DBConnectionUrl: %r"
                            % type(mysql_connection_url))
        super(MySQLStorageWrapper, self).__init__(**kwargs)
        self._mysql_connection_url = mysql_connection_url
        self._mysql_config = mysql_config or {}
        self._ra_sender = ra_sender

    def _setup(self):
        super(MySQLStorageWrapper, self)._setup()
        self._l(LOG).info("Configuring RA storage...")
        # Configure user-api storage
        engines.engine_factory.configure_factory(
            db_url=self._mysql_connection_url.url,
            config=self._mysql_config,
            query_cache=True,
            sender=self._ra_sender,
        )
