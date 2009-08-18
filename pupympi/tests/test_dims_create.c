#include "mpi.h"
#include <stdio.h>

int prodof( int, const int[] );
/*
* Test edge cases of Dims_create
*/
int prodof( int ndims, const int dims[] )
{
    int i, prod=1;
    for (i=0; i<ndims; i++)
        prod *= dims[i];
    return prod;
}

int main( int argc, char *argv[] )
{
    int errs = 0;
    int dims[4], nnodes;

    printf("Init\n");
    fflush(stdout);
    MPI_Init( &argc, &argv );

    printf("2D tests\n");
    fflush(stdout);
    /* 2 dimensional tests */
    for (nnodes=1; nnodes <= 32; nnodes = nnodes * 2) {
        dims[0] = 0;
        dims[1] = nnodes;

        printf("2D dims_create: %d\n", nnodes);
        fflush(stdout);
        MPI_Dims_create( nnodes, 2, dims );
        if (prodof(2, dims) != nnodes) {
            errs++;
            printf( "Dims_create returned the wrong decomposition. " );
            printf( "Is [%d x %d], should be 1 x %d\n", dims[0], dims[1], nnodes );
            fflush(stdout);
        }

        printf("2D dims_create, all locked: %d\n", nnodes);
        fflush(stdout);
        /* Try calling Dims_create with nothing to do (all dimensions specified) */
        dims[0] = 1;
        dims[1] = nnodes;
        MPI_Dims_create( nnodes, 2, dims );
        if (prodof(2, dims) != nnodes) {
            errs++;
            printf( "Dims_create returned the wrong decomposition (all given). " );
            printf( "Is [%d x %d], should be 1 x %d\n", dims[0], dims[1], nnodes );
            fflush(stdout);
        }
    }

    /* 4 dimensional tests */
    for (nnodes=4; nnodes <= 64; nnodes = nnodes + 2) {
        /*dims[0] = 0;
        dims[1] = nnodes/2;
        dims[2] = 0;
        dims[3] = 2;*/
        dims[0] = 0;
        dims[1] = 0;
        dims[2] = 0;
        dims[3] = 0;

        printf("4D dims_create: %d: ", nnodes);
        fflush(stdout);
        MPI_Dims_create( nnodes, 4, dims );
        if (prodof(4, dims) != nnodes) {
            errs++;
            printf( "Dims_create returned the wrong decomposition. " );
            printf( "Is [%d x %d x %d x %d], should be 1 x %d x 1 x 2\n", dims[0], dims[1], dims[2], dims[3], nnodes/2 );
            fflush(stdout);
        }
        printf( "Is [%d x %d x %d x %d]\n", dims[0], dims[1], dims[2], dims[3] );
        fflush(stdout);

       /* printf("4D dims_create, all locked: %d\n", nnodes);
        fflush(stdout);
        // Try calling Dims_create with nothing to do (all dimensions specified) 
        dims[0] = 1;
        dims[1] = nnodes/2;
        dims[2] = 1;
        dims[3] = 2;
        MPI_Dims_create( nnodes, 2, dims );
        if (prodof(4, dims) != nnodes) {
            errs++;
            printf( "Dims_create returned the wrong decomposition (all given). " );
            printf( "Is [%d x %d x %d x %d], should be 1 x %d x 1 x 2\n", dims[0], dims[1], dims[2], dims[3], nnodes/2 );
            fflush(stdout);
        }
        */
    }

    MPI_Finalize();
    return errs;
}
