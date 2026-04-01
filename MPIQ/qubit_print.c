/**
 * @file qubit_print.c
 * @brief Qubit waveform data printing utility
 *
 * This module provides a formatted print function for three-dimensional qubit waveform
 * arrays. It compresses consecutive repeated values into "repeat N times" summaries
 * for more readable output during debugging and diagnostics.
 *
 * This module is part of the MPIQ library.
 */
#include "MPIQ.h"
/**
 * @brief Print qubit waveform data in a compressed format
 *
 * Prints the three-dimensional qubit waveform array information. Consecutive repeated
 * values are compressed into "repeat N times" summaries for readability.
 *
 * @param[in] qubit       Three-dimensional array of qubit waveform data
 * @param[in] qubit_count Total number of qubits
 * @param[in] arry_counts Array recording the length of each qubit waveform array
 */
void qubit_print(char ***qubit, int qubit_count, int *arry_counts)
{
    for (int i = 0; i < qubit_count; i++)
    {
        // Repetition is used to record the number of repetitions.
        int repetition = 0;
        for (int j = 0; j < arry_counts[i]; j++)
        {
            if (j == 0)
            {
                printf("qubit_%d: %s ", i, qubit[i][j]);
                if (strcmp(qubit[i][j], qubit[i][j + 1]) == 0)
                {
                    repetition++;
                }
            }
            else if (j == (arry_counts[i] - 1))
            {
                if (repetition == 0)
                    printf("%s\n", qubit[i][j]);
                else
                {
                    repetition++;
                    printf("repeat %d times\n", repetition);
                }
            }
            else
            {
                if (repetition == 0)
                {
                    printf("%s ", qubit[i][j]);
                    if (strcmp(qubit[i][j], qubit[i][j + 1]) == 0)
                    {
                        repetition++;
                    }
                }
                else
                {
                    repetition++;
                    if (strcmp(qubit[i][j], qubit[i][j + 1]))
                    {
                        printf("repeat %d times ", repetition);
                        repetition = 0;
                    }
                }
            }
        }
    }
}