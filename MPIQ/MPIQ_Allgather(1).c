/**
 * @file MPIQ_allgather.c
 * @brief MPIQ all-gather communication module for quantum processing systems
 *
 * This module implements the MPIQ_Allgather function, which enables a classical process
 * to collect quantum bit waveform data from all other classical processes in the communication
 * domain. It serves as a central point for aggregating results from distributed quantum-classical
 * computations.
 *
 * Key functionalities include:
 * - Sending gather commands to all other classical processes
 * - Receiving quantum bit count information from each process
 * - Collecting waveform data points for each quantum bit
 * - Formatted printing of the gathered quantum bit waveform data
 * - Proper memory management for received data buffers
 *
 * This module is part of the MPIQ library, which extends MPI functionality
 * for quantum-classical hybrid computing applications.
 */

#include "MPIQ.h"

/**
 * @brief Gather quantum bit waveform data from all classical processes
 *
 * This function collects quantum bit waveform data from all other classical processes
 * in the communication domain to the calling process. It implements a distributed collection
 * mechanism where each target process responds to a gather command by transmitting its
 * quantum bit waveform data.
 *
 * @param[in] comm MPIQ_Comm structure defining the communication domain
 * @param[in] rank Rank/sequence number of the current classical process
 * @return 0 on successful data collection and printing
 *
 * @note This function assumes classical-classical communication mode is enabled
 * @note The function uses MPI for inter-process communication
 * @attention Each data point is assumed to be 25 bytes in length
 * @warning The function prints data directly to stdout; no data storage is provided
 */
int MPIQ_Allgather(MPIQ_Comm comm, int rank)
{
    if (rank == 0)
    {
        // Iterate through all classical processes in the communication domain
        // Skip the current process (don't gather data from ourselves)
        for (int i = 0; i < comm.size; i++)
        {
            if (i != rank)
            {
                // Send the gather command to the target process
                // BUG FIX (v29->v30): The original code used sizeof(send_token) which equals 8
                // (pointer size on 64-bit), sending only the pointer address bytes instead of
                // the actual string content. Changed to strlen+1 to send the complete string.
                char *send_token = "gather";
                MPI_Send(send_token, strlen(send_token) + 1, MPI_CHAR, i, 0, comm.mpi_comm);
                char ***qubit = NULL;    // Quantum bit data storage
                int q_count;             // Number of quantum bits to receive
                int *arry_counts = NULL; // Number of data points per quantum bit
                char **wave_arry;

                // Receive the number of quantum bits from the target process
                MPI_Recv(&q_count, 1, MPI_INT, i, 1, comm.mpi_comm, MPI_STATUS_IGNORE);
                // Receive and print waveform data for each quantum bit
                for (int m = 0; m < q_count; m++)
                {
                    int arry_count = 0;
                    // Receive the number of data points for this quantum bit
                    MPI_Recv(&arry_count, 1, MPI_INT, i, 1, comm.mpi_comm, MPI_STATUS_IGNORE);
                    arry_counts = (int *)realloc(arry_counts, (m + 1) * sizeof(int));
                    arry_counts[m] = arry_count;
                    qubit = (char ***)realloc(qubit, (m + 1) * sizeof(char **));
                    wave_arry = NULL;
                    // Receive and print each waveform data point for this quantum bit
                    for (int n = 0; n < arry_count; n++)
                    {
                        // Allocate memory for waveform data point
                        char *recv_wave = (char *)malloc(25 * sizeof(char));

                        // Receive waveform data (25 bytes per data point)
                        MPI_Recv(recv_wave, 25, MPI_CHAR, MPI_ANY_SOURCE, 2, comm.mpi_comm, MPI_STATUS_IGNORE);

                        wave_arry = (char **)realloc(wave_arry, (n + 1) * sizeof(char *));
                        wave_arry[n] = (char *)malloc(strlen(recv_wave) + 1); // Prevent buffer overflow
                        strcpy(wave_arry[n], recv_wave);

                        // Free allocated memory for this data point
                        free(recv_wave);
                    }
                    qubit[m] = wave_arry;
                }
                printf("all_gather result:\n");
                qubit_print(qubit, q_count, arry_counts);
                printf("send result_qubit to all cards...\n");
                MPIQ_Bcast(q_count, arry_counts, qubit, comm);

                printf("send result_qubit to all classical progresses...\n");
                // Write received quantum bit data to file
                FILE *fp;
                char filename[50];
                sprintf(filename, "../data/allgather_result%d.txt", rank + 1);
                fp = fopen(filename, "w");
                if (fp == NULL)
                {
                    perror("Failed to open file for writing");
                    // Continue execution even if file writing fails
                }
                else
                {
                    // Write qubit count
                    fprintf(fp, "%d\n", q_count);
                    // Write data point counts for each qubit
                    for (int i = 0; i < q_count; i++)
                    {
                        fprintf(fp, "%d ", arry_counts[i]);
                    }
                    fprintf(fp, "\n");
                    // Write the actual quantum bit waveform data
                    for (int i = 0; i < q_count; i++)
                    {
                        for (int j = 0; j < arry_counts[i]; j++)
                        {
                            fprintf(fp, "%s ", qubit[i][j]);
                        }
                        fprintf(fp, "\n");
                    }
                    fclose(fp);
                    printf("Successfully wrote received data to %s\n", filename);
                }

                free(arry_counts);
                // BUG FIX (v29->v30): The wave_arry pointer has already been stored as qubit[m]
                // in the qubit array. If free(wave_arry) is called here, a subsequent
                // free(qubit[m]) would cause a double-free (undefined behavior).
                // Correct approach: free only via free(qubit) uniformly; do not free wave_arry separately here.
                // free(wave_arry);  // Removed to avoid double-free
                free(qubit);
                wave_arry = NULL;
                arry_counts = NULL;
                qubit = NULL;
            }
        }
    }
    else
    {
        int q_count;             // Number of quantum bits to gather
        int *arry_counts = NULL; // Array storing counts of waveform data points per qubit

        // Gather local quantum bit data
        char ***qubit = MPIQ_Gather(comm, &q_count, &arry_counts);
        printf("Gather is over...\n");

        // Allocate memory for receiving control commands
        char *send_token = (char *)malloc(10 * sizeof(char));

        // Receive the gather command from the root process
        MPI_Recv(send_token, 8, MPI_CHAR, MPI_ANY_SOURCE, 0, comm.mpi_comm, MPI_STATUS_IGNORE);

        // If the command is to gather data
        if (strcmp(send_token, "gather") == 0)
        {
            // Send the number of quantum bits to the root process
            MPI_Send(&q_count, 1, MPI_INT, 0, 1, comm.mpi_comm);

            // For each quantum bit
            for (int i = 0; i < q_count; i++)
            {
                // Send the number of waveform data points
                MPI_Send(&(arry_counts[i]), 1, MPI_INT, 0, 1, comm.mpi_comm);

                // Send each waveform data point
                for (int j = 0; j < arry_counts[i]; j++)
                {
                    // Send the waveform information
                    MPI_Send(qubit[i][j], 25, MPI_CHAR, 0, 2, comm.mpi_comm);
                }
            }
        }

        printf("send result_qubit to all classical progresses...\n");
        // Write received quantum bit data to file
        FILE *fp;
        char filename[50];
        sprintf(filename, "../data/allgather_result%d.txt", rank + 1);

        fp = fopen(filename, "w");
        if (fp == NULL)
        {
            perror("Failed to open file for writing");
            // Continue execution even if file writing fails
        }
        else
        {
            // Write qubit count
            fprintf(fp, "%d\n", q_count);
            // Write data point counts for each qubit
            for (int i = 0; i < q_count; i++)
            {
                fprintf(fp, "%d ", arry_counts[i]);
            }
            fprintf(fp, "\n");
            // Write the actual quantum bit waveform data
            for (int i = 0; i < q_count; i++)
            {
                for (int j = 0; j < arry_counts[i]; j++)
                {
                    fprintf(fp, "%s ", qubit[i][j]);
                }
                fprintf(fp, "\n");
            }
            fclose(fp);
            printf("Successfully wrote received data to %s\n", filename);
        }

        // Free allocated memory
        free(send_token);

        // Clean up quantum bit data structures
        for (int i = 0; i < q_count; i++)
        {
            for (int j = 0; j < arry_counts[i]; j++)
            {
                free(qubit[i][j]);
            }
            free(qubit[i]);
        }
        free(qubit);
        free(arry_counts);
    }

    // Return success
    return 0;
}
