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

from loopster import exceptions as loopster_exc


class WatchDogBaseException(loopster_exc.LoopsterException):
    msg_template = "Watchdog base exception"


class WatchDogCriticalException(WatchDogBaseException):
    msg_template = "Watchdog critical exception: %(reason)r"


class WatchDogMinorException(WatchDogBaseException):
    msg_template = "Watchdog minor exception: %(reason)r"


class LockCriticalException(WatchDogCriticalException):
    msg_template = "Locking critical exception"


class LockMinorException(WatchDogMinorException):
    msg_template = "Locking minor exception"


class ServiceHeartbeatTimeout(WatchDogCriticalException):
    msg_template = ("Service heartbeat timed out at %(check_time)s:"
                    " %(delta)s > %(timeout)s (last: %(last_heartbeat)s)")


class ServiceIsMarkedFailed(WatchDogCriticalException):
    msg_template = "Service is marked as failed."


class ServiceLockTimedOut(LockMinorException):
    msg_template = "Service acquired lock has timed out."


class ServiceLockNotAcquired(LockMinorException):
    msg_template = "Service lock acquisition failed."


class ServiceLockRefreshTimedOut(LockMinorException):
    msg_template = "Service lock refresh failed due to timeout."
