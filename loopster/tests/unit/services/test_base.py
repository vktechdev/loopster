# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2022 VK Cloud.
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
import unittest

import mock

from loopster.services import base

LOG = logging.getLogger(__name__)


class TestService(base.AbstractService):

    def _serve(self):
        pass

    def stop(self):
        pass


class BaseAbstractServiceTestCase(unittest.TestCase):

    @mock.patch('loopster.services.base.AbstractService._serve_fake')
    @mock.patch('loopster.services.base.AbstractService._serve_operational')
    def test_enabled_service(self, serve_operational, serve_fake):
        s = TestService()

        s.serve()

        serve_operational.assert_called_once()
        serve_fake.assert_not_called()

    @mock.patch('loopster.services.base.AbstractService._serve_fake')
    @mock.patch('loopster.services.base.AbstractService._serve_operational')
    def test_not_enabled_service(self, serve_operational, serve_fake):
        s = TestService(operate=False)

        s.serve()

        serve_operational.assert_not_called()
        serve_fake.assert_called_once()
