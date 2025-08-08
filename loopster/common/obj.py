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

import binascii
import logging
import os
import weakref


class BaseLoggerAdapter(logging.LoggerAdapter):

    def __init__(self, logger, obj):
        super(BaseLoggerAdapter, self).__init__(logger, {})
        self._obj = obj
        self._obj_id = self._obj._obj_id
        self._obj_type_name = self._obj.__class__.__name__

    def process(self, msg, kwargs):
        template = "[%s:%s] %s"
        return template % (self._obj_type_name, self._obj_id, msg), kwargs


class BaseObject(object):

    def __new__(cls, *args, **kwargs):
        if args:
            raise TypeError("%s accepts kwargs only" % cls)
        inst = super(BaseObject, cls).__new__(cls)
        inst._init_kwargs = kwargs
        return inst

    def __init__(self, obj_id=None):
        super(BaseObject, self).__init__()
        if obj_id is None:
            self._obj_id = binascii.hexlify(os.urandom(4))
        else:
            self._obj_id = obj_id
        self._loggers = {}

    def _l(self, logger):
        # use `.get()` to avoid any exceptions for _log_exception()
        wrapped = self._loggers.get(logger)
        if wrapped is None:
            wrapped = BaseLoggerAdapter(logger, weakref.proxy(self))
            self._loggers[logger] = wrapped
        return wrapped

    def __repr__(self):
        t = type(self)
        klass = "%s.%s" % (t.__module__, t.__name__)
        kwargs = ["%s=%r" % (k, v) for k, v in self._init_kwargs.items()]
        return "%s(%s)" % (klass, ", ".join(kwargs))
