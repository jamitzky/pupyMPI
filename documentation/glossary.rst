****************************
 Glossary 
****************************


.. glossary::

   mpirun
      The program used to start your MPI programs. Accepts parameters like the
      amount of instances to start, which program to run etc. Read more at the
      :ref:`mpirun documentation page <mpirun>`. 
      
   communicator
      Holds information about a specific rank execution along with communication
      information used to reach other ranks part of the same communicator. 

   tag
      A integer you specify on a message allowing you do filter the kind of
      messages you wan't to receive. These tags are restricted as described
      under :ref:`the tag rules <tagrules>`
