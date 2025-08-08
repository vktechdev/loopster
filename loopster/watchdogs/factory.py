# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright 2021 Mail.ru Group.
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

import importlib

from loopster.watchdogs import base as wd_base
from loopster.watchdogs.exceptions import WatchDogCriticalException

ETCD_TYPE = 'etcd'
TIMED_TYPE = 'timed'
DUMMY_TYPE = 'dummy'

VALID_WATCHDOG_TYPES = (ETCD_TYPE, TIMED_TYPE, DUMMY_TYPE)


def create_etcd_config(endpoints=None, namespace=None, timeout=None):
    try:
        etcd_client = importlib.import_module('httpetcd.clients')
    except ImportError:
        raise ImportError('Install httpetcd for etcd support')

    return etcd_client.Config(endpoints=endpoints,
                              namespace=namespace,
                              timeout=timeout)


def create_etcd_watchdog(heartbeat_timeout, etcd_config, lock_key,
                         lock_ttl=None, unsafe_lock_ttl=False):
    """Create instance of watchdog that rely on timing + master control."""
    # etcd support is optional
    try:
        wd_etcd = importlib.import_module('loopster.watchdogs.etcd')
    except ImportError:
        raise ImportError('Install httpetcd for etcd support')

    return wd_etcd.WatchDogEtcd(heartbeat_timeout=heartbeat_timeout,
                                etcd_config=etcd_config,
                                lock_key=lock_key,
                                lock_ttl=lock_ttl,
                                unsafe_lock_ttl=unsafe_lock_ttl)


def create_timed_watchdog(heartbeat_timeout):
    """Create instance of watchdog that rely on timing."""
    return wd_base.WatchDog(heartbeat_timeout=heartbeat_timeout)


def create_dummy_watchdog():
    """Create instance of watchdog that does nothing."""
    return wd_base.WatchDogBase()


def get_watchdog(watchdog_type, **kwargs):
    """Return specific type of watchdog depending on requested arguments."""
    watchdog_instance = None

    if watchdog_type == ETCD_TYPE:
        watchdog_instance = create_etcd_watchdog(**kwargs)

    elif watchdog_type == TIMED_TYPE:
        watchdog_instance = create_timed_watchdog(kwargs['heartbeat_timeout'])

    elif watchdog_type == DUMMY_TYPE:
        watchdog_instance = create_dummy_watchdog()

    if watchdog_instance is not None:
        return watchdog_instance

    raise WatchDogCriticalException(
        reason=('Watchdog type must be specified. '
                'Allowed variants: {valid}. Given variant: {got}').format(
            valid=', '.join(VALID_WATCHDOG_TYPES),
            got=repr(watchdog_type)
        )
    )
