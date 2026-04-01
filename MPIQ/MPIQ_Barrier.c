/**
 * @file MPIQ_Barrier.c
 * @brief MPIQ global barrier synchronization module
 *
 * This module implements the MPIQ_Barrier function, which synchronizes multiple
 * quantum processes in quantum-classical hybrid computing. The barrier mechanism
 * uses TCP sockets + POSIX threads:
 *   - Process 0 acts as the coordinator, listening for ready signals from other processes;
 *   - Other processes send a ready signal and block until process 0 sends a "go" release signal;
 *   - After process 0 receives all signals, it notifies all processes to proceed simultaneously.
 *
 * This module is part of the MPIQ library, extending MPI functionality to support
 * quantum-classical hybrid computing.
 */
#include "MPIQ.h"
#include <time.h>

volatile int signal_num = 0;
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;

// Thread arguments now include a flag to indicate if the release signal has been sent
// (for process 0 to reclaim connections)
typedef struct
{
    int client_socket;
    int *released; // Shared array, marking whether the corresponding client has been released
    int index;     // Client index (0~size-2, corresponding to processes 1~size-1)
} ThreadArgs;

/**
 * Thread handler function: Receives signals from clients and waits for the unified release signal from process 0.
 */
void *receive_signal(void *arg)
{
    ThreadArgs *args = (ThreadArgs *)arg;
    int client_socket = args->client_socket;
    char buffer[1024] = {0};

    // 1. Receive signal from the client (e.g., "right")
    ssize_t valread = read(client_socket, buffer, sizeof(buffer) - 1);
    if (valread > 0)
    {
        printf("Process 0 received signal: %s (from client %d)\n", buffer, args->index + 1);

        // Decrement the signal counter
        pthread_mutex_lock(&mutex);
        if (signal_num > 0)
        {
            signal_num--;
        }
        pthread_mutex_unlock(&mutex);
    }
    else if (valread < 0)
    {
        perror("Failed to read signal");
    }

    // 2. Wait for the release signal from the main thread of process 0 (blocks until notified by the main thread)
    while (args->released[args->index] == 0)
    {
        // BUG FIX (v29->v30): sleep() takes an unsigned int parameter; passing 0.001 is
        // truncated to 0, causing a busy-wait at 100% CPU.
        // Changed to usleep(1000) to sleep for 1ms, properly reducing CPU usage.
        usleep(1000); // 休眠 1ms 以减少 CPU 占用
    }

    // 3. Send the release signal to the client
    const char *go_signal = "go";
    send(client_socket, go_signal, strlen(go_signal), 0);
    printf("Process 0: Release signal sent to client %d\n", args->index + 1);

    // 4. Clean up resources
    close(client_socket);
    free(args);
    pthread_exit(NULL);
}

int MPIQ_Barrier(MPIQ_Comm comm, int server_id)
{
    int rank, size;
    rank = server_id;                        // rank from server_id parameter
    size = (comm.size > 0) ? comm.size : 2;  // dynamic size from comm, fallback to 2
    signal_num = size - 1;

    const char *signal = "right";
    const int port = 8888;

    if (rank != 0)
    {
        // Non-zero processes: Send a signal, then wait for the release signal from process 0
        int sockfd;
        struct sockaddr_in server_addr;

        // Create a socket and connect to process 0
        if ((sockfd = socket(AF_INET, SOCK_STREAM, 0)) < 0)
        {
            perror("Client: socket creation failed");
            exit(EXIT_FAILURE);
        }
        server_addr.sin_family = AF_INET;
        server_addr.sin_port = htons(port);
        if (inet_pton(AF_INET, "127.0.0.1", &server_addr.sin_addr) <= 0)
        {
            perror("Client: Invalid IP address");
            close(sockfd);
            exit(EXIT_FAILURE);
        }
        if (connect(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
        {
            perror("Client: Connection failed");
            close(sockfd);
            exit(EXIT_FAILURE);
        }

        // Send signal to process 0
        send(sockfd, signal, strlen(signal), 0);
        printf("Process %d: Signal sent, waiting for release...\n", rank);

        // Wait for the release signal from process 0 (blocking read)
        char go_buf[16] = {0};
        read(sockfd, go_buf, sizeof(go_buf) - 1);
        if (strcmp(go_buf, "go") == 0)
        {
            printf("Process %d: Release signal received\n", rank);
        }

        // Close the connection
        close(sockfd);
    }
    else
    {
        // Process 0: After receiving all signals, send a release signal to each client
        int server_fd;
        struct sockaddr_in server_addr, client_addr;
        socklen_t client_len = sizeof(client_addr);
        pthread_t *threads = malloc((size - 1) * sizeof(pthread_t));
        int *released = calloc(size - 1, sizeof(int)); // Array to mark if a client has been released (0: not released, 1: released)

        if (!threads || !released)
        {
            perror("Server: Memory allocation failed");
            exit(EXIT_FAILURE);
        }

        // Create and configure the server socket
        if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) < 0)
        {
            perror("Server: socket creation failed");
            free(threads);
            free(released);
            exit(EXIT_FAILURE);
        }
        int opt = 1;
        setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
        server_addr.sin_family = AF_INET;
        server_addr.sin_addr.s_addr = INADDR_ANY;
        server_addr.sin_port = htons(port);
        if (bind(server_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
        {
            perror("Server: Bind failed");
            close(server_fd);
            free(threads);
            free(released);
            exit(EXIT_FAILURE);
        }
        if (listen(server_fd, size - 1) < 0)
        {
            perror("Server: Listen failed");
            close(server_fd);
            free(threads);
            free(released);
            exit(EXIT_FAILURE);
        }
        printf("Process 0: Starting to receive signals (total %d expected)\n", size - 1);

        // Accept all client connections and create threads
        for (int i = 0; i < size - 1; i++)
        {
            int client_socket = accept(server_fd, (struct sockaddr *)&client_addr, &client_len);
            if (client_socket < 0)
            {
                perror("Server: Failed to accept connection");
                free(threads);
                free(released);
                close(server_fd);
                exit(EXIT_FAILURE);
            }

            // Pass the client socket, release flag array, and index to the thread
            ThreadArgs *args = malloc(sizeof(ThreadArgs));
            args->client_socket = client_socket;
            args->released = released;
            args->index = i;
            if (pthread_create(&threads[i], NULL, receive_signal, args) != 0)
            {
                perror("Server: Thread creation failed");
                close(client_socket);
                free(args);
                free(threads);
                free(released);
                close(server_fd);
                exit(EXIT_FAILURE);
            }
        }

        // Wait for all signals to be received (signal_num decrements to 0)
        while (signal_num > 0)
        {
        // BUG FIX (v29->v30): Same issue as above — sleep(0.001) was truncated to sleep(0),
        // causing a busy-wait. Changed to usleep(1000).
            usleep(1000);
        }
        printf("Process 0: All signals received, starting to send release signals...\n");

        // Notify all threads that they can send the release signal (modify the shared flag)
        for (int i = 0; i < size - 1; i++)
        {
            released[i] = 1; // The thread will detect this flag and send "go" to the client
        }

        // Wait for all threads to complete
        for (int i = 0; i < size - 1; i++)
        {
            pthread_join(threads[i], NULL);
        }

        // Free resources
        close(server_fd);
        free(threads);
        free(released);
    }

    // All processes have been released from the barrier.
    return 0;
}
