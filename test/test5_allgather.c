/**
 * @file test_all_gather.c
 * @brief Test program for MPIQ_Allgather functionality
 *
 * This module tests the MPIQ_Allgather operation, which collects quantum bit waveform
 * data from all processes in the MPIQ communicator to the root process. The program
 * demonstrates how to initialize a MPIQ environment and use the all-gather operation
 * in a distributed computing context.
 *
 * The test follows a simple pattern:
 * - Process with rank 0 acts as the coordinator and initiates the all-gather operation
 * - Other processes gather data locally and then respond to the coordinator's requests
 * - Data is exchanged using both MPIQ and standard MPI communication primitives
 *
 * This test is part of the verification suite for the MPIQ library, which extends
 * MPI functionality for quantum-classical hybrid computing applications.
 */

#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "../MPIQ/MPIQ.h"
#include <sys/wait.h>
#include <string.h>

/**
 * @brief Main function for testing MPIQ_Allgather
 *
 * Initializes the MPIQ environment and coordinates the all-gather test operation.
 * The root process (rank 0) initiates the all-gather operation, while other processes
 * gather local data and wait for and respond to communication requests from the root.
 *
 * @param argc Number of command-line arguments
 * @param argv Array of command-line arguments
 * @return 0 on successful execution
 */
int main(int argc, char **argv)
{
    int rank;                // Process rank within the communicator
    char token[] = "CC";     // Communication token for MPIQ initialization
    MPI_Datatype qubit_wave; // Custom MPI datatype for quantum bit waveforms

    // Initialize MPIQ environment
    MPIQ_Comm comm = MPIQ_Init(&argc, &argv, &rank, token, &qubit_wave);

    // Process with rank 0 acts as coordinator. Other processes act as data providers
    // Execute the MPIQ_Allgather operation to collect data from all processes
    MPIQ_Allgather(comm, rank);

    // Finalize MPI environment
    MPI_Finalize();

    return 0;
}