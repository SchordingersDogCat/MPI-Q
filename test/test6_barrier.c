#include <stdio.h>
#include <string.h>
#include "../MPIQ/MPIQ.h"

int main(int argc, char *argv[])
{
    QubitConfig ***cfg = NULL; /* Clear all */
    // QubitConfig *ip_card_configs[10][10];
    QubitConfig ***ip_card_configs = NULL;
    int **card_count;
    char file[] = "../demo/test.qasm";
    int rank;
    // initialize the communication domain.
    MPIQ_Comm comm = MPIQ_Init(&argc, &argv, &rank, NULL, NULL);
    // get qubit config from json
    cfg = parse_qubit_configs_v2("../conf/config.json", ip_card_configs, &card_count);
    if (cfg == NULL)
    {
        fprintf(stderr, " parse_self fail\n");
        return 1;
    }

    printf(" ======== before bcast ========\n");
    int q_count;
    int *arry_counts = NULL;
    char ***qubit = NULL;
    // get qubit
    qubit = qasm_to_pulse_waveforms(&q_count, &arry_counts, file);
    // exec MPIQ_broadcast
    if (MPIQ_Bcast(q_count, arry_counts, qubit, rank, comm) < 0)
    {
        fprintf(stderr, "bcast fail\n");
        return 1;
    }

    printf("======== after bcast ========\n");
    return 0;
}