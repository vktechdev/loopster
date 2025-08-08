.. Loopster's documentation master file, created by
   sphinx-quickstart on Sun Aug  5 14:13:14 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Welcome to loopster's documentation!
====================================

Loopster - Service library

.. toctree::
    :maxdepth: 2
    :caption: Оглавление:

    releasenotes

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


Examples
========

Hub with services as processes, stop on service state difference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

    from loopster.hubs import base
    from loopster.hubs.controllers import panic
    from loopster.hubs.drivers import process
    from loopster.services import softirq

    class BasicService(softirq.SoftIrqService):
        def _step(self):
            time.sleep(10)

    driver = process.ProcessDriver()
    controller = panic.PanicController()
    hub = base.BaseHub(driver=driver, controller=controller)

    hub.add_service(svc_class=BasicService, svc_kwargs={})
    hub.serve()

Nested service usage (example with mysqlwrapper)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. code-block:: python

    from restalchemy.storage.sql import engines
    from loopster.services import mysql

    svc_with_mysql = mysql.MySQLStorageWrapper(
        nested_class=MY_MAIN_SERVICE,
        nested_kwargs=dict(
            'MY_ARG'='MY_VAL'),
        mysql_connection_url=engines.DBConnectionUrl(MY_DB_URL))

    svc_with_mysql.serve()

Public interface
================

Services
~~~~~~~~

.. automodule:: loopster.services.softirq
    :members:
    :inherited-members:

.. automodule:: loopster.services.bjoern
    :members:
    :inherited-members:


Hub
~~~

.. automodule:: loopster.hubs.base
    :members:

Controllers
~~~~~~~~~~~

.. automodule:: loopster.hubs.controllers.force_state
    :members:
    :inherited-members:

.. automodule:: loopster.hubs.controllers.panic
    :members:
    :inherited-members:

Drivers
~~~~~~~

.. automodule:: loopster.hubs.drivers.process
    :members:
    :inherited-members:
