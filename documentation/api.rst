.. _api: 

API documentation
===================================

This chapter contains documentation of the pupyMPI API. It's further divided by a number of
subsections. 

   The MPI object
        A singleton class containing the main handle to the MPI environment.
   
   The communicators
        It's through the communicators the main communication between processes
        is handled. Each communicator contains a number of members and all 
        communication in a communicator must be between members. When the MPI
        object is initialized a single communicator called MPI_COMM_WORLD exists
        containing all started processes as members.

   The reuqest objects
        Some communication calls returns a request handle. Through this handle
        it's possible to control a number of things for that communication. 
  
   Semantics for custom operations in collective calls
        Some collective calls like scan, reduce and allreduce allows the users
        to define custom functions used to calculate the final result. Those 
        functions should uphold some specification. 

.. toctree::

    The main MPI object <api_mpi>
    Communicators <api_communicator>
    The request objects <api_request>
    Operations <api_operations>

