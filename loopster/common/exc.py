# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright 2011 OpenStack Foundation
#    Copyright 2019-2021 Mail.ru Group.
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

import contextlib
import logging
import sys

import six


LOG = logging.getLogger(__name__)


@contextlib.contextmanager
def suppress_any(msg=None, level=logging.ERROR, exc_info=True, adapter=None):
    try:
        yield
    except Exception:
        msg = msg or "Nested exception ignored:"
        logger = LOG if adapter is None else adapter(LOG)
        logger.log(level, msg, exc_info=exc_info)


@contextlib.contextmanager
def reraise_original(msg=None, level=logging.ERROR, exc_info=True,
                     adapter=None):
    _exc_info = sys.exc_info()
    try:
        yield
    except Exception:
        msg = msg or "Nested exception ignored:"
        logger = LOG if adapter is None else adapter(LOG)
        logger.log(level, msg, exc_info=exc_info)
    finally:
        six.reraise(*_exc_info)


@contextlib.contextmanager
def raise_default():
    exc_info = sys.exc_info()
    yield
    six.reraise(*exc_info)
