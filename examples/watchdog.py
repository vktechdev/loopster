# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
#    Copyright 2019 Mail.ru Group.
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

from logging import config as logging_config
import random
import time

from loopster.hubs import base
from loopster.hubs.controllers import force_state
from loopster.hubs.drivers import process
from loopster.services import softirq
from loopster.watchdogs import base as wd_base


DEFAULT_CONFIG = {
    'version': 1,
    'formatters': {
        'aardvark': {
            'datefmt': '%Y-%m-%d,%H:%M:%S',
            'format': "%(asctime)15s.%(msecs)03d %(processName)s"
                      " pid:%(process)d tid:%(thread)d %(levelname)s"
                      " %(name)s:%(lineno)d %(message)s"
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'aardvark',
            'stream': 'ext://sys.stdout'
        },
    },
    'loggers': {
        'loopster': {},
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console']
    }
}


class MyServiceWithSimpleWatchdog(softirq.SoftIrqService):

    def _step(self):
        for i in range(5):
            time.sleep(random.randint(0, 5))


def main():
    logging_config.dictConfig(DEFAULT_CONFIG)

    driver = process.ProcessDriver()
    controller = force_state.AlwaysForceTargetStateController()
    hub = base.BaseHub(driver=driver, controller=controller)

    watchdog = wd_base.WatchDog(heartbeat_timeout=10)

    hub.add_service(svc_class=MyServiceWithSimpleWatchdog,
                    svc_kwargs={'watchdog': watchdog})
    hub.serve()


if __name__ == "__main__":
    main()
