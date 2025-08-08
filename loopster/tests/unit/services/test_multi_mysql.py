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

import unittest

import mock

from loopster.services import base
from loopster.services import multi_mysql


class FakeService(base.AbstractService):

    def _serve(self):
        pass

    def stop(self):
        pass


class MultiMySQLStorageWrapperTestCase(unittest.TestCase):
    """Test case for MultiMySQLStorageWrapper instance"""

    def test_validate_missing_default(self):
        self.assertRaises(ValueError,
                          multi_mysql.MultiMySQLStorageWrapper)
        self.assertRaises(ValueError,
                          multi_mysql.MultiMySQLStorageWrapper,
                          multi_mysql.MultiMySQLEngineUnit("fake",
                                                           engine_name="x"))

    def test_validate_multi_default(self):
        self.assertRaises(ValueError,
                          multi_mysql.MultiMySQLStorageWrapper,
                          multi_mysql.MultiMySQLEngineUnit("fake"),
                          multi_mysql.MultiMySQLEngineUnit("fake_2"))

    @mock.patch('restalchemy.storage.sql.engines'
                '.engine_factory.configure_factory')
    def test_validate_multi(self, factory_mock):
        svc = multi_mysql.MultiMySQLStorageWrapper(
            multi_mysql.MultiMySQLEngineUnit("fake_default"),
            multi_mysql.MultiMySQLEngineUnit("fake_another",
                                             engine_name="another"),
            nested_class=FakeService,
            nested_kwargs={}
        )
        svc._setup()
