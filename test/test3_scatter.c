#include <stdio.h>
#include <string.h>
#include "../MPIQ/MPIQ.h"

int main(int argc, char *argv[])
{
    printf("======== before scatter ========\n");
    QubitConfig ***cfg = NULL;
    // QubitConfig *ip_card_configs[10][10];
    QubitConfig ***ip_card_configs = NULL;
    int **card_count = NULL;
    int rank;
    // initialize the communication domain.
    MPIQ_Comm comm = MPIQ_Init(&argc, &argv, &rank, NULL, NULL);
    char ***send_q = NULL;
    int q_count;
    int *arry_counts;
    char file[] = "../demo/test.qasm";
    // get qubit config from json
    cfg = parse_qubit_configs_v2("../conf/config.json", ip_card_configs, &card_count);
    if (cfg == NULL)
    { /* Just read the rank0 entry */
        fprintf(stderr, "[root] parse_self fail\n");
        return 1;
    }

    int ip_count = 0;
    for (int i = 0; i < comm.count;)
    {
        for (int card_id = 0; card_id < comm.card_id_count[ip_count]; card_id++)
        {
            send_q = (char ***)realloc(send_q, (i + 1) * sizeof(char **));
            char **qbit = NULL;
            for (int q = 0; q <= card_count[ip_count][card_id + 1]; q++)
            {
                qbit = (char **)realloc(qbit, (q + 1) * sizeof(char *));
                qbit[q] = (char *)malloc(25 * sizeof(char));
                if (q == card_count[ip_count][card_id + 1])
                {
                    strcpy(qbit[q], "end");
                }
                else
                {
                    // The reason why card_id needs to be added 1 is that the board numbering starts from 1.
                    strcpy(qbit[q], cfg[ip_count][card_id + 1][q].name);
                }
            }
            send_q[i] = qbit;
            i++;
        }
        ip_count++;
    }

    char ***total_qubit = qasm_to_pulse_waveforms(&q_count, &arry_counts, file);

    if (MPIQ_Scatter(send_q, comm, total_qubit, q_count, arry_counts) < 0)
    {
        fprintf(stderr, "scatter fail\n");
        return 1;
    }

    /* ========== Verification ========== */
    printf("======== after scatter ========\n");
    // print_cfg(&recvbuf);
    return 0;
}
