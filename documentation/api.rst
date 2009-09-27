.. _api: 

The pupympi API documentation
===================================

This is a general documentation of the API part. Please find
information about binaries etc other places. 

Table of contents
-----------------------------------

.. toctree::
    :maxdepth: 1

    The main MPI object <api_mpi>
    The request objects <api_request>
    Communicators <api_communicator>
    Operations <api_operations>

The main MPI object
======================================================================================
This is the object you use when you start your program. 

Read about them under :doc:`api_mpi`.

Request objects
======================================================================================
Handles you receive when doing fancy communication. 

Read about them under :doc:`api_request`.

Communicators
======================================================================================
Main object type you'll use to communicate between your processes. 

Read about them under :doc:`api_communicator`.

Operations 
=============================================================================================================================================================================================================================
Operations are *special* functions used in operations like allreduce. pupympi
comes with a handfull, python has functions that qualify and you can write your
own off cause. 

Read about them under :doc:`api_operations`

