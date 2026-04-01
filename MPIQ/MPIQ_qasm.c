/**
 * @file MPIQ_qasm.c
 * @brief MPIQ QASM file filtering and qubit extraction module
 *
 * This module provides the functionality to filter QASM (Quantum Assembly Language)
 * instructions by qubit name, generating sub-QASM files that contain only the
 * instructions relevant to the target qubits, for subsequent pulse waveform conversion.
 *
 * Key functionalities:
 *   - convert_qubit_to_q: Converts "qubit_N" format names to QASM "q[N]" reference format
 *   - should_keep_line: Determines whether a QASM instruction line is relevant to the target qubits
 *   - extract_q: Extracts target qubit-related lines from a source QASM file and writes to a new file
 *
 * This module is part of the MPIQ library, supporting task distribution in
 * quantum-classical hybrid computing.
 */
#include "MPIQ.h"

/**
 * @brief Convert "qubit_N" format qubit name to QASM reference format "q[N]"
 *
 * @param[in] input Qubit name string in the format "qubit_0"
 * @return Dynamically allocated string in the format "q[N]"; caller is responsible for free()
 *
 * @note Only supports single-character indices (0-9); multi-digit indices require extending this function
 * @warning The returned string is allocated via malloc; the caller must free it
 */
char *convert_qubit_to_q(const char *input)
{
    char *output = malloc(5 * sizeof(char));
    int j = 0;
    output[j] = 'q';
    output[++j] = '[';
    output[++j] = input[6]; // Extract the 7th character of "qubit_N", i.e., the index N
    output[++j] = ']';
    output[++j] = '\0'; // End Marker
    return output;
}

/**
 * @brief Determine whether a line in a QASM file should be retained
 *
 * Retention rules:
 *   1. Retain basic QASM framework lines (header declarations, register definitions)
 *   2. Retain instruction lines containing references to the target qubits
 *
 * @param[in] line   Current line content from the QASM file
 * @param[in] name   Target qubit name array, terminated with an "end" string
 * @return true if the line should be retained, false otherwise
 */
bool should_keep_line(const char *line, char **name)
{
    // Preserve the basic framework of the QASM.
    if (strstr(line, "OPENQASM 2.0;") != NULL ||
        strstr(line, "include \"qelib1.inc\";") != NULL ||
        strstr(line, "qreg q[") != NULL ||
        strstr(line, "creg c[") != NULL)
    {
        return true;
    }

    // Select the required quantum bit-related statements.
    for (int i = 0;; i++)
    {
        if (strcmp(name[i], "end") == 0)
        {
            break;
        }
        else if (strstr(line, convert_qubit_to_q(name[i])) != NULL)
        {
            printf("%s ", name[i]);
            return true;
        }
    }

    return false;
}

/**
 * @brief Extract instructions for specified qubits from a QASM file and write to a new file
 *
 * This function reads the input QASM file line by line, calls should_keep_line() to
 * determine whether to retain each line, and writes retained lines to the output file.
 * Used to split multi-qubit QASM circuits by hardware partitions.
 *
 * @param[in] input_filename   Source QASM file path
 * @param[in] output_filename  Target output file path
 * @param[in] name             Target qubit name array, terminated with an "end" string
 *
 * @note If the input or output file cannot be opened, the program exits with EXIT_FAILURE
 */
void extract_q(const char *input_filename, const char *output_filename, char **name)
{
    FILE *input_file = fopen(input_filename, "r");
    FILE *output_file = fopen(output_filename, "w");

    if (!input_file)
    {
        perror("Failed to open input file");
        exit(EXIT_FAILURE);
    }

    if (!output_file)
    {
        perror("Failed to open output file");
        fclose(input_file);
        exit(EXIT_FAILURE);
    }

    char line[256];
    while (fgets(line, sizeof(line), input_file))
    {
        // Check whether the current line needs to be retained
        if (should_keep_line(line, name))
        {
            fputs(line, output_file);
        }
    }
    printf("\n");

    printf("Successfully extracted relevant content to %s\n", output_filename);

    fclose(input_file);
    fclose(output_file);
}