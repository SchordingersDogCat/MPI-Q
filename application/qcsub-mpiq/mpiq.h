/**
 * @file mpiq.h
 * @brief MPIQ unified communication interface header
 *
 * This header provides two layers of MPIQ communication:
 *
 * 1. Application-layer file transfer (MPIQ_Send / MPIQ_Recv / MPIQ_Send_Results)
 *    Used by mpiq_user.c and mpiq_monitor.c for sending/receiving QASM files
 *    and simulation results between user and monitor processes.
 *
 * 2. Quantum-level waveform data transfer (MPIQ_SendQubits / MPIQ_RecvQubits)
 *    Merged from ./MPIQ/ library. Used for sending/receiving quantum bit waveform
 *    data to/from quantum processing boards over TCP with request-response protocol.
 */

#ifndef MPIQ_H
#define MPIQ_H

#include <sys/socket.h>
#include <netinet/in.h>
#include <mpi.h>

/* ============================================================
 * Common definitions
 * ============================================================ */

#ifndef MPIQ_BUFFER_SIZE
#define MPIQ_BUFFER_SIZE 4096
#endif

#ifndef MPIQ_LARGE_BUFFER_SIZE
#define MPIQ_LARGE_BUFFER_SIZE 65536
#endif

#define MAX_PATH_LEN 512
#define MAX_FILES 100

/* ============================================================
 * MPIQ_Comm — Communication domain structure
 *   Merged from ./MPIQ/MPIQ.h
 * ============================================================ */

typedef struct
{
    char **ip_addr;       /* Array of IP address strings                          */
    int *card_id_count;   /* Number of cards per IP                               */
    int count;            /* Total number of IP entries                           */
    MPI_Comm mpi_comm;    /* MPI communicator                                     */
    int size;             /* Number of processes in the communication domain      */
} MPIQ_Comm;

/* ============================================================
 * Application-layer file transfer functions (original)
 * ============================================================ */

/**
 * @brief Send QASM files from a folder to a monitor process
 *
 * @param ip           Target IP address
 * @param port         Target port number
 * @param folder_path  Path to the folder containing QASM files
 * @param subcircuit_idx  Subcircuit index for header identification
 * @return 0 on success, -1 on error
 */
int MPIQ_Send(const char *ip, int port, const char *folder_path, int subcircuit_idx);

/**
 * @brief Send simulation result files back to the user process
 *
 * @param ip           Target IP address
 * @param port         Target port number
 * @param folder_path  Path to the folder containing result files
 * @return 0 on success, -1 on error
 */
int MPIQ_Send_Results(const char *ip, int port, const char *folder_path);

/**
 * @brief Receive files (QASM or results) from a sender
 *
 * @param port         Port to listen on
 * @param output_dir   Directory to save received files
 * @param expected_subcircuit_idx  Expected subcircuit index for validation
 * @return 0 on success, -1 on error
 */
int MPIQ_Recv(int port, const char *output_dir, int expected_subcircuit_idx);

/* ============================================================
 * Quantum-level waveform data transfer functions (merged from ./MPIQ/)
 * ============================================================ */

/**
 * @brief Send quantum bit waveform data to a quantum processing board
 *
 * Establishes a TCP connection to a quantum processing board and sends
 * quantum bit waveform data using a reliable request-response protocol.
 * Port = 5000 + card_id.
 *
 * @param qubit_count  Number of quantum bits to send
 * @param arry_counts  Array: number of data points per qubit
 * @param qubit        3D array: qubit[qubit_idx][point_idx] waveform string
 * @param ip           IP address of the quantum processing board
 * @param card_id      Card ID (used to calculate port: 5000 + card_id)
 * @param comm         MPIQ_Comm communication domain
 * @return 0 on success, -1 on error
 */
int MPIQ_SendQubits(int qubit_count, int *arry_counts, char ***qubit,
                    char *ip, int card_id, MPIQ_Comm comm);

/**
 * @brief Receive quantum bit waveform data from a quantum processing board
 *
 * Establishes a TCP connection and receives qubit waveform data using a
 * reliable request-response protocol with comma-separated value parsing.
 * Port = 5000 + card_id.
 *
 * @param ip           IP address of the quantum processing board
 * @param card_id      Card ID (used to calculate port: 5000 + card_id)
 * @param qubit_count  [out] Number of quantum bits received
 * @param arry_counts  [out] Array: data points per qubit (caller must free)
 * @param comm         MPIQ_Comm communication domain
 * @return 3D array of waveform data (caller must free), or NULL on error
 */
char ***MPIQ_RecvQubits(char *ip, int card_id, int *qubit_count,
                        int **arry_counts, MPIQ_Comm comm);

/**
 * @brief Print quantum bit waveform data (debug utility)
 */
void qubit_print(char ***qubit, int qubit_count, int *arry_counts);

#endif /* MPIQ_H */
