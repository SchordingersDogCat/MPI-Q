/**
 * @file MPIQ_scatter.c
 * @brief MPIQ data scattering module for quantum processing systems
 *
 * This module implements the MPIQ_Scatter function, which is responsible for
 * distributing quantum bit waveform data from a classical process to multiple
 * quantum processing boards based on a predefined mapping. It serves as a
 * sophisticated task distribution mechanism that enables quantum workload
 * partitioning across distributed quantum hardware.
 *
 * Key functionalities include:
 * - Reading QASM files containing quantum circuit descriptions
 * - Extracting relevant quantum bits based on predefined mapping
 * - Converting QASM instructions to pulse waveforms for quantum hardware
 * - Distributing specific quantum bits to their assigned processing boards
 * - Managing memory allocation and deallocation for temporary data structures
 *
 * This module is part of the MPIQ library, which extends MPI functionality
 * for quantum-classical hybrid computing applications.
 */

#include "MPIQ.h"

/**
 * @brief Scatter quantum bit waveform data to specific quantum processing boards
 *
 * This function implements a specialized distribution mechanism that assigns specific
 * quantum bits to designated quantum processing boards according to a predefined mapping.
 * It performs a complete workflow from quantum circuit description to hardware-specific
 * pulse waveform transmission.
 *
 * @param[in] send_q Three-dimensional array defining the mapping between boards and quantum bits
 * @param[in] comm MPIQ_Comm structure defining the communication domain
 * @param[in] qubit Three-dimensional array containing quantum bit waveform data
 * @param[in] qubit_count Number of quantum bits to send
 * @param[in] arry_counts Array containing the number of data points for each quantum bit
 * @return 0 on successful distribution of data to all boards
 *
 * @note The send_q array has the following structure:
 * @note send_q = {
 * @note   {"qubit_0", "qubit_1", "end"},
 * @note   {"qubit_2", "qubit_3", "end"}
 * @note }
 * @note Where each sub-array represents a board, containing quantum bit identifiers
 * @note and terminated with an "end" marker
 *
 * @attention File paths for QASM input/output are hardcoded
 * @warning Ensure the mapping in send_q correctly matches the available hardware resources
 * @note This function calls extract_q and qasm_to_pulse_waveforms to process QASM files
 */
int MPIQ_Scatter(char ***send_q, MPIQ_Comm comm, char ***qubit, int qubit_count, int *arry_counts)
{
  // Define input and output file paths
  int ip_count = 0; // Counter for IP addresses in comm structure

  // Iterate through all boards in the communication domain
  for (int i = 0; i < comm.count;)
  {
    // Iterate through each board associated with the current IP address
    for (int card_id = 0; card_id < comm.card_id_count[ip_count]; card_id++)
    {
      char ***temp_qubit = NULL;
      int temp_q_count = 0;         // Number of quantum bits to send to this board
      int *temp_arry_counts = NULL; // Array containing data point counts

      // Extract relevant quantum bits from QASM file based on the mapping
      printf("dest:%s:%d\n", comm.ip_addr[ip_count], (card_id + 1));
      printf("send_qubit:");
      for (int send = 0;; send++)
      {
        if (strcmp(send_q[i][send], "end") == 0)
        {
          printf("\n");
          break;
        }
        else
        {
          printf(" %s", send_q[i][send]);
          temp_q_count++;
          temp_qubit = (char ***)realloc(temp_qubit, sizeof(char **) * (send + 1));
          temp_qubit[send] = qubit[(send_q[i][send][6] - '0')];
          temp_arry_counts = (int *)realloc(temp_arry_counts, sizeof(int) * (send + 1));
          temp_arry_counts[send] = arry_counts[(send_q[i][send][6] - '0')];
        }
      }

      // Send quantum bit data to the board (note: board numbering starts from 1)

      MPIQ_Send(temp_q_count, temp_arry_counts, temp_qubit, comm.ip_addr[ip_count], (card_id + 1), comm);

      i++; // Move to next entry in the send_q mapping array
    }
    ip_count++; // Move to next IP address
  }

  // Return success
  return 0;
}
