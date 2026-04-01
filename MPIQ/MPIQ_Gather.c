/**
 * @file MPIQ_gather.c
 * @brief MPIQ data gathering module for quantum processing systems
 *
 * This module implements the MPIQ_Gather function, which is responsible for
 * collecting and merging quantum bit waveform data from multiple quantum processing
 * boards to a central classical process. It implements a specialized merging algorithm
 * that prioritizes non-zero values when combining data from different sources.
 *
 * Key functionalities include:
 * - Iterating through all quantum processing boards in the communication domain
 * - Receiving quantum bit waveform data from each board
 * - Merging data using a prioritized approach (non-zero values overwrite zero values)
 * - Detecting data completeness based on predefined tokens
 * - Dynamic memory management for the merged dataset
 *
 * This module is part of the MPIQ library, which extends MPI functionality
 * for quantum-classical hybrid computing applications.
 */

#include "MPIQ.h"

/**
 * @brief Gather quantum bit waveform data from quantum processing boards
 *
 * This function collects quantum bit waveform data from all quantum processing boards
 * in the communication domain. It implements a specialized merging algorithm where
 * non-zero values from any board overwrite zero values in the accumulated result.
 * The gathering process continues until all boards have been processed or until
 * a completeness token is detected.
 *
 * @param[in] comm MPIQ_Comm structure defining the communication domain
 * @param[out] qubit_count Total number of quantum bits gathered
 * @param[out] arry_counts Array containing the number of data points for each quantum bit
 * @return Three-dimensional array containing the gathered and merged quantum bit waveform data
 *
 * @note The function stops gathering when it encounters a token indicating data completeness
 * @note The caller is responsible for freeing the returned memory
 * @attention Memory for the returned data structures is dynamically allocated
 * @warning The merging algorithm prioritizes non-zero values regardless of their source
 */
char ***MPIQ_Gather(MPIQ_Comm comm, int *qubit_count, int **arry_counts)
{
    char ***qubit = NULL; // 3D array to store the final gathered data
    bool token = true;    // Flag to determine when to stop gathering

    // Iterate through each IP address and its associated boards in the communication domain
    for (int i = 0; i < comm.count; i++)
    {
        for (int j = 1; j < comm.card_id_count[i] + 1; j++)
        {
            token = true;          // Reset token for each board
            int qubit_num = 0;     // Number of qubits received from current board
            int *arry_nums = NULL; // Data point counts for current board

            // Receive quantum bit waveform data from the current board
            char ***temp = MPIQ_Recv(comm.ip_addr[i], j, &qubit_num, &arry_nums, comm);
            printf("%s:%d: \n", comm.ip_addr[i], j);
            qubit_print(temp, qubit_num, arry_nums);

            // If this is the first board to respond, initialize the result array
            if (qubit == NULL)
            {
                qubit = temp;
                token = false;
            }
            // Merge data from the current board with the accumulated result
            // Non-zero values from any board overwrite zero values in the result
            for (int m = 0; m < qubit_num; m++)
            {
                for (int n = 0; n < arry_nums[m]; n++)
                {
                    // If both values are zero, keep token as false (continue gathering)
                    if (strcmp(qubit[m][n], "0") == 0 && strcmp(temp[m][n], "0") == 0)
                    {
                        token = false;
                    }
                    // If current result is zero but new value is not, update the result
                    else if (strcmp(qubit[m][n], "0") == 0 && strcmp(temp[m][n], "0") != 0)
                    {
                        strcpy(qubit[m][n], temp[m][n]);
                    }
                    // Note: If current result is non-zero, it is kept regardless of new value
                    // This implements the prioritization of the first non-zero value encountered
                }
            }
            // Stop gathering if token indicates data completeness
            if (token)
            {
                break;
            }

            // Update output parameters with the current board's metadata
            *qubit_count = qubit_num;
            *arry_counts = arry_nums;
        }

        // Stop gathering if token indicates data completeness across all boards for this IP
        if (token)
        {
            break;
        }
    }

    // Write gathered quantum bit data to file
    FILE *fp;
    char filename[] = "../data/gather_result.txt";

    fp = fopen(filename, "w");
    if (fp == NULL)
    {
        perror("Failed to open file for writing");
        // Continue execution even if file writing fails
    }
    else
    {
        // Write qubit count
        fprintf(fp, "%d\n", *qubit_count);

        // Write data point counts for each qubit
        for (int i = 0; i < *qubit_count; i++)
        {
            fprintf(fp, "%d ", (*arry_counts)[i]);
        }
        fprintf(fp, "\n");

        // Write the actual quantum bit waveform data
        for (int i = 0; i < *qubit_count; i++)
        {
            for (int j = 0; j < (*arry_counts)[i]; j++)
            {
                fprintf(fp, "%s ", qubit[i][j]);
            }
            fprintf(fp, "\n");
        }

        fclose(fp);
        printf("Successfully wrote gathered data to %s\n", filename);
    }

    // Return the gathered and merged quantum bit waveform data
    return qubit;
}
