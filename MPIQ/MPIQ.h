/* The MPIQ library, which contains the definitions of various communication functions of MPIQ
   and some auxiliary sub-functions for these communication functions.

   MPIQ (Classical-Quantum Message Passing Interface) is a distributed communication protocol
   designed for "classical + quantum" hybrid computing architectures. It provides standardized
   programming interfaces compatible with classical MPI models, enabling communication between
   classical computing nodes and quantum measurement-control boards.
*/
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 199309L
#endif
#ifndef MPIQ_H
#define MPIQ_H
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "cJSON.h"
#include <stdbool.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdbool.h>
#include <mpi.h>
#include <pthread.h>
#include <omp.h>

/** @brief Size of communication buffers used in Send/Recv operations (64 KB) */
#define BUFFERSIZE 65536

// Define qubit configuration structure
typedef struct
{
    char name[20];         // e.g. "qubit_0"
    char ip[20];           // IP address
    int card_id;           // Card ID
    int channel_id;        // Channel ID
    int waveshape;         // Waveform
    double freq_Hz;        // Frequency
    double ampl;           // Amplitude
    double phase_rad;      // Phase
    double dc_offset;      // DC offset
    double sample_rate_Hz; // Sample rate
} QubitConfig;

typedef struct
{
    char **ip_addr;
    int *card_id_count;
    int count;
    MPI_Comm mpi_comm;
    int size;
} MPIQ_Comm;

char ***qasm_to_pulse_waveforms(int *q_count, int **a_counts, char *file);

QubitConfig ***parse_qubit_configs_v2(const char *json_file, QubitConfig ***ip_card_configs, int ***card_count);

int MPIQ_Send(int qubit_count, int *arry_counts, char ***qubit, char *ip, int card_id, MPIQ_Comm comm);

char ***MPIQ_Recv(char *ip, int card_id, int *qubit_count, int **arry_counts, MPIQ_Comm comm);

MPIQ_Comm MPIQ_Init(int *argc, char ***argv, int *rank, char *comm_token, MPI_Datatype *qubit_wave);

MPIQ_Comm MPIQ_Init_ex(int *argc, char ***argv, int *rank, char *comm_token, MPI_Datatype *qubit_wave, const char *config_path);

int MPIQ_Bcast(int q_count, int *arry_counts, char ***qubit, int size, MPIQ_Comm send_data);

int MPIQ_Scatter(char ***send_q, MPIQ_Comm comm, char ***qubit, int qubit_count, int *arry_counts);

char ***MPIQ_Gather(MPIQ_Comm comm, int *qubit_count, int **arry_counts);

int MPIQ_Allgather(MPIQ_Comm comm, int rank);

void extract_q(const char *input_filename, const char *output_filename, char **name);

void qubit_print(char ***qubit, int qubit_count, int *arry_counts);

int MPIQ_Barrier(MPIQ_Comm comm, int server_id);

#endif
