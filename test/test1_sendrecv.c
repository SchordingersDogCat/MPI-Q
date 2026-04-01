#include <stdio.h>
#include <stdlib.h>
#include <mpi.h>
#include "../MPIQ/MPIQ.h"
#include <sys/wait.h>
#include <string.h>

int main(int argc, char **argv)
{
    MPIQ_Comm comm = MPIQ_Init(&argc, &argv, NULL, NULL, NULL);
    char file[] = "../demo/test.qasm";
    char ***qubit;
    char ***result;
    int qubit_send_count = 0, qubit_recv_count = 0;
    int *arry_send_counts = NULL;
    int *arry_recv_counts = NULL;
    // QubitConfig *ip_card_configs[10][10];
    QubitConfig ***ip_card_configs = NULL;
    int **card_count;
    // get qubit config from json
    QubitConfig ***icc = parse_qubit_configs_v2("../conf/config.json", ip_card_configs, &card_count);
    // get qubit
    qubit = qasm_to_pulse_waveforms(&qubit_send_count, &arry_send_counts, file);

    // qubit_print_modulated_waveforms(qubit, qubit_send_count, arry_send_counts);

    // exec MPIQ_send
    MPIQ_Send(qubit_send_count, arry_send_counts, qubit, icc[0][1][0].ip, icc[0][1][0].card_id, comm);
    // free memory space
    for (int i = 0; i < qubit_send_count; i++)
    {
        for (int j = 0; j < arry_send_counts[i]; j++)
        {
            free(qubit[i][j]);
            qubit[i][j] = NULL;
        }
        free(qubit[i]);
        qubit[i] = NULL;
    }
    free(qubit);
    free(arry_send_counts);
    result = MPIQ_Recv("127.0.0.1", 1, &qubit_recv_count, &arry_recv_counts, comm);
    // qubit_print(result, qubit_recv_count, arry_recv_counts);
    // free memory space
    for (int i = 0; i < qubit_recv_count; i++)
    {
        for (int j = 0; j < arry_recv_counts[i]; j++)
        {
            free(result[i][j]);
            result[i][j] = NULL;
        }
        free(result[i]);
        result[i] = NULL;
    }
    free(result);
    result = NULL;
}
