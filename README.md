# Loopster

Loopster is a service library that provides mechanisms for executing and managing services, including monitoring their status and automatically restarting them when necessary.

## Installation

To install Loopster, you can use pip:

```
pip install loopster
```

## Usage

### Basic Service Example

Here's an example of how to create and run a basic service using Loopster:

```python
from loopster.hubs import base
from loopster.hubs.controllers import panic
from loopster.hubs.drivers import process
from loopster.services import softirq

class BasicService(softirq.SoftIrqService):
    def _step(self):
        print("Hello, world!")

driver = process.ProcessDriver()
controller = panic.PanicController()
hub = base.BaseHub(driver=driver, controller=controller)

hub.add_service(svc_class=BasicService, svc_kwargs={})
hub.serve()
```

### Nested Service Example with MySQLWrapper

Here's an example of how to use a nested service with the `mysqlwrapper` module:

```python
from restalchemy.storage.sql import engines
from rooster.hubs.controllers import force_state
from loopster.hubs.drivers import process
from loopster.services import mysql
from loopster.services import softirq

class BasicService(softirq.SoftIrqService):
    def _step(self):
        print("Hello, world!")

hub = process.ProcessHub(
    controller=force_state.AlwaysForceTargetStateController())

hub.add_service(
    svc_class=mysql.MySQLStorageWrapper,
    svc_kwargs=dict(
        nested_class=BasicService,
        nested_kwargs=dict(
            step_period=STEP_PERIOD,
        ),
        mysql_connection_url=engines.DBConnectionUrl(CONNECTION_URL)
    )
)
```

## Public Interface

### Services

Loopster provides several built-in services, including:

- `SoftIrqService`: A service with a watchdog that runs in an infinite loop.
- `BjoernService`: A special server for Bjoern, which implements multiprocessing by itself.

### Hubs
The `ProcessHub` class is used to manage multiple services using one strategy provided by the driver. It inherits from `SoftIrqService`, so it's a service too!

Hub provides a simple way to start and stop multiple services at once, as well as monitor their status.

#### Features

- **Signal Handling**: The `ProcessHub` can handle signals such as SIGHUP and SIGUSR1, allowing for graceful shutdowns and other terminal actions.
- **Multiprocessing Support**: By using the `multiprocessing` module, `ProcessHub` ensures that services run in separate processes, providing better isolation and resource management.
- **State Management**: The hub manages the state of each service, ensuring they are running as expected and automatically restarting them when necessary.

### Controllers

Loopster includes different controllers that manage the state of services:

- `AlwaysForceTargetStateController`: A simple controller that always sets states in a loop.
- `PanicController`: A controller that stops managing on any problem.

### Drivers

The `ProcessDriver` class is used to serve services as child processes. It provides methods for adding, removing, and setting the state of services.
