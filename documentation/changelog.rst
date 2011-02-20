Releases
=================================================================

Changes to version 0.9.1:
-----------------------------------------------------------------
* Made it possible to configure pupyMPI with a custom settings module.

Changes to version 0.9.0:
-----------------------------------------------------------------
* Added non blocking collective operations. 

Changes to version 0.8.0:
-----------------------------------------------------------------

* Introduced migration and utilities: 
* Added a utils/pupy_abort.py utility for aborting a running instance (bromer)
* Added a utils/pupy_ping.py utility for testing if a running instance is "running" (bromer)
* Added a utils/pupy_readregisters.py utility for reading user defined registers (bromer)
* Added a utils/pupy_pack.py utility for migrating one instance to another (bromer)

Changes to version 0.7.4:
-----------------------------------------------------------------

* Cruft cleaning for reduce and bcast in CollectiveRequest (fhantho)
* Added TCP_NODELAY to all sockets (asser)

Changes to version 0.7.3:
-----------------------------------------------------------------

* Only attempt an accept() call on the main server socket instead of all sockets.

Changes to version 0.7.2:
-----------------------------------------------------------------

* Split handling of in and out sockets in select/poll functions and for in thread and out thread

Changes to version 0.7.1:
-----------------------------------------------------------------

* Handle writelist only when outgoing requests exist

Changes to version 0.7.0:
-----------------------------------------------------------------

* Implemented use of poll and epoll (Linux only)
* Added initial support for Kqueue (BSD only)

Changes to version 0.6:
-----------------------------------------------------------------

* Initial pupyMPI release

