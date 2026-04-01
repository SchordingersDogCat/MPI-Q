/*
 * Server Card Manager
 *
 * This program initializes an MPI environment and spawns child processes
 * for each available card using fork() and execv(). It manages the lifecycle
 * of these server card processes and collects their exit statuses.
 *
 * Dependencies:
 * - MPI library
 * - MPIQ library (Custom MPI wrapper)
 */

#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <mpi.h>
#include "../MPIQ/MPIQ.h"

/**
 * Main function that initializes MPI, spawns server card processes,
 * and waits for their completion.
 *
 * @param argc Argument count
 * @param argv Argument vector
 * @return Exit status
 */
int main(int argc, char **argv)
{
    int rank, total_ranks;

    /* Initialize MPIQ communication structure */
    MPIQ_Comm comm = MPIQ_Init(NULL, NULL, NULL, NULL, NULL);

    /* Initialize MPI environment */
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &total_ranks);

    /* Array to store process IDs of spawned server card processes */
    pid_t pid_cards[comm.card_id_count[rank]];

    /* Spawn a child process for each card assigned to this rank */
    for (int card_id = 0; card_id < comm.card_id_count[rank]; card_id++)
    {
        pid_t pid = fork();

        if (pid == -1)
        {
            /* Error handling for fork failure */
            printf("fork() failed: Unable to create child process\n");
            return 1;
        }
        else if (pid == 0)
        {
            /* Child process: Set up port and execute server_card */
            char PORT[7];
            sprintf(PORT, "%d", card_id + 5001);
            char *args[] = {"./server_card", comm.ip_addr[rank], PORT, NULL};

            /* Replace current process with server_card */
            execv("./server_card", args);

            /* This point is only reached if execv fails */
            printf("execv() failed: Unable to execute program\n");
            exit(EXIT_FAILURE);
        }
        else
        {
            /* Parent process: Store child PID and report status */
            pid_cards[card_id] = pid;
            printf("card_id:%d is running\n", card_id + 1);
        }
    }

    /* Wait for all child processes to complete */
    for (int i = 0; i < comm.card_id_count[rank]; i++)
    {
        int status;
        pid_t wait_pid = waitpid(pid_cards[i], &status, 0); // Wait for specific child process

        if (wait_pid == -1)
        {
            perror("waitpid failed\n");
            exit(EXIT_FAILURE);
        }

        /* Report completion status of the child process */
        printf("card_id:%d (PID=%d) has completed, exit status:%d\n",
               i + 1, wait_pid, WEXITSTATUS(status));
    }

    /* Finalize MPI environment */
    MPI_Finalize();

    return 0;
}