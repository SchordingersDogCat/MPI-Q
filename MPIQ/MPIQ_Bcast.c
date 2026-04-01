/**
 * @file MPIQ_broadcast.c
 * @brief MPIQ broadcast communication module for quantum processing systems
 *
 * This module implements the MPIQ_Broadcast function, which is responsible for
 * distributing quantum bit waveform data from a classical process to all quantum
 * processing boards registered in the communication domain. It serves as a central
 * mechanism for task distribution in quantum-classical hybrid computing workflows.
 *
 * Key functionalities include:
 * - Iterating through all IP addresses in the communication domain
 * - Processing each quantum board associated with each IP address
 * - Reusing the MPIQ_Send function for individual board communication
 * - Providing uniform data distribution across all quantum hardware
 *
 * This module is part of the MPIQ library, which extends MPI functionality
 * for quantum-classical hybrid computing applications.
 */

#include <omp.h>
#include "MPIQ.h"
#include <errno.h>
// BUG FIX (v29->v30): Added missing header. The fork() version uses wait(),
// which requires <sys/wait.h>; otherwise wait() is undeclared on some platforms.
#include <sys/wait.h>
/**
 * @brief Broadcast quantum bit waveform data to all quantum processing boards
 *
 * This function implements a classical-to-quantum broadcast operation, sending
 * the same quantum bit waveform data to all quantum processing boards registered
 * in the communication domain. It performs this by iterating through each IP address
 * and its associated boards, invoking MPIQ_Send for each target.
 *
 * @param[in] q_count Number of quantum bits to broadcast
 * @param[in] arry_counts Array containing the number of data points for each quantum bit
 * @param[in] qubit Three-dimensional array containing quantum bit waveform data
 * @param[in] comm MPIQ_Comm structure defining the communication domain
 * @return 0 on successful broadcast to all boards
 *
 * @note This function calls MPIQ_Send for each board in the communication domain
 * @attention Ensure the MPIQ_Comm structure is properly initialized before calling this function
 * @warning All boards must be operational to complete the broadcast successfully
 */
int MPIQ_Bcast(int q_count, int *arry_counts, char ***qubit, MPIQ_Comm comm)
{
    // Iterate through each IP address in the communication domain
    for (int i = 0; i < comm.count; i++)
    {
        // Iterate through each board associated with the current IP address
        for (int j = 1; j <= comm.card_id_count[i]; j++)
        {
            // Send quantum bit data to the specific board
            MPIQ_Send(q_count, arry_counts, qubit, comm.ip_addr[i], j, comm);
        }
    }

    // Print completion message
    printf("All the data has been sent...\n");

    // Return success
    return 0;
}
