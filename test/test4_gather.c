#include <stdio.h>
#include <string.h>
#include "../MPIQ/MPIQ.h"

int main(int argc, char *argv[])
{
    int rank;
    MPIQ_Comm comm = MPIQ_Init(&argc, &argv, &rank, NULL, NULL);
    printf(" ---- before gather ----\n");
    // q_count is the number of qubit
    int q_count;
    // arry_count is the number of arry
    int *arry_counts = NULL;
    // exec MPIQ_gather
    char ***qubit = MPIQ_Gather(comm, &q_count, &arry_counts);
    printf("gather over...\n");
    qubit_print(qubit, q_count, arry_counts);
    // free its memory space
    for (int i = 0; i < q_count; i++)
    {
        for (int j = 0; j < arry_counts[i]; j++)
        {
            free(qubit[i][j]);
            qubit[i][j] = NULL;
        }
        free(qubit[i]);
        qubit[i] = NULL;
    }
    free(qubit);
    free(arry_counts);
    qubit = NULL;
    printf("---- after gather ----\n");
    return 0;
}